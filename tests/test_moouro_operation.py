# Copyright  Alexandre Díaz <dev@redneboa.es>
import xmlrpc.client as xmlrpclib
import time
import re
import json
from conftest import project_compose_up, wait_for_odoo, wait_for_patroni_leader


class TestMoouroOperation:
    IMG_GREEN = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUl"
        + "EQVR42mNk+M/wHwAEBgIApD5fRAAAAABJRU5ErkJggg=="
    )

    def test_operation(
        self, docker_env, env_info, exec_docker_db, run_docker_db_no_entrypoint
    ):
        common_url = (
            f"http://{env_info['ip']}:{env_info['ports']['odoo']}/xmlrpc/common"
        )
        sock_url = f"http://{env_info['ip']}:{env_info['ports']['odoo']}/xmlrpc/object"
        db = "odoodb"
        username = "admin"
        password = "admin"
        odoo_ver = env_info["options"]["odoo_version"]
        image_field = "image" if float(odoo_ver) < 13 else "image_1920"

        common = xmlrpclib.ServerProxy(common_url)
        uid = common.login(db, username, password)
        sock = xmlrpclib.ServerProxy(sock_url)

        # Create Records
        partner_a = sock.execute(
            db,
            uid,
            password,
            "res.partner",
            "create",
            {
                "name": "Partner A",
                image_field: self.IMG_GREEN,
            },
        )
        assert partner_a > 0
        partner_b = sock.execute(
            db,
            uid,
            password,
            "res.partner",
            "create",
            {
                "name": "Partner B",
            },
        )
        assert partner_b > 0

        # Launch Backup
        output = exec_docker_db(["moouro_backup"])
        assert (
            "backup command end: completed successfully" in output.lower()
            and re.search(r"snapshot\s+\w+\s+saved", output.lower())
        )

        # Get Backup Info
        info = exec_docker_db(["pgbackrest", "--stanza=main", "info", "--output=json"])
        backups = json.loads(info)
        latest_backup_set = (
            backups[0]["backup"][-1]["label"]
            if isinstance(backups, list)
            else backups["backup"][-1]["label"]
        )
        assert latest_backup_set.endswith("F")

        # Write Record B
        result = sock.execute(
            db,
            uid,
            password,
            "res.partner",
            "write",
            [partner_b],
            {"name": "Partner B MOD", image_field: self.IMG_GREEN},
        )
        assert result is True

        # Down All
        docker_env.compose.down(remove_orphans=True)

        # Launch Restore (latest state without WAL)
        output = run_docker_db_no_entrypoint(["moouro_restore", "/var/lib/odoo/data"])
        assert "restore command end: completed successfully" in output.lower()

        # Up Services
        project_compose_up(env_info["client_type"], docker_env)
        wait_for_odoo(env_info["ip"], env_info["ports"]["odoo"])

        # Check Record A
        result = sock.execute(
            db, uid, password, "res.partner", "read", [partner_a], [image_field, "name"]
        )
        assert result[0]["name"] == "Partner A"
        assert result[0][image_field] == self.IMG_GREEN

        # Check Record B
        result = sock.execute(
            db, uid, password, "res.partner", "read", [partner_b], [image_field, "name"]
        )
        assert result[0]["name"] == "Partner B"
        assert not result[0][image_field]

    def test_replica(
        self, docker_env, env_info, exec_docker_db, run_docker_db_no_entrypoint
    ):
        output = run_docker_db_no_entrypoint(["moouro_init_replica"], replica=True)
        assert "pg_basebackup done" in output
        project_compose_up(env_info["client_type"], docker_env, services=["db-replica"])
        timeout = 500  # Free runners can be very slow
        start_time = time.time()
        in_recovery = False
        while time.time() - start_time < timeout:
            try:
                output = exec_docker_db(
                    [
                        "psql",
                        "-U",
                        "postgres",
                        "-d",
                        "odoodb",
                        "-t",
                        "-c",
                        "SELECT pg_is_in_recovery();",
                    ],
                    replica=True,
                )
                if output.strip() == "t":
                    in_recovery = True
                    break
            except Exception:
                pass
            time.sleep(2)
        assert in_recovery
        count = exec_docker_db(
            [
                "psql",
                "-U",
                "postgres",
                "-d",
                "odoodb",
                "-t",
                "-c",
                "SELECT COUNT(*) FROM ir_module_module;",
            ],
            replica=True,
        )
        assert int(count.strip()) > 0


class TestPatroniOperation:
    def test_patroni_leader_elected(self, patroni_env, exec_patroni):
        output = exec_patroni(
            "patroni1",
            ["patronictl", "-c", "/etc/patroni/config.yml", "list"],
        )
        assert "Leader" in output

    def test_patroni_write_read_failover(self, patroni_env, exec_patroni):
        ip = patroni_env["ip"]
        api_ports = patroni_env["api_ports"]
        leader_api_port = patroni_env["leader_api_port"]

        leader_node = "patroni1" if leader_api_port == api_ports["patroni1"] else "patroni2"
        follower_node = "patroni2" if leader_node == "patroni1" else "patroni1"

        # Write a row on the current leader
        out = exec_patroni(
            leader_node,
            [
                "psql",
                "-U",
                "postgres",
                "-c",
                (
                    "CREATE TABLE IF NOT EXISTS patroni_test (id SERIAL, value TEXT);"
                    " INSERT INTO patroni_test (value) VALUES ('before_failover');"
                ),
            ],
        )
        assert "INSERT" in out

        # Trigger a manual failover to the other node
        exec_patroni(
            leader_node,
            [
                "patronictl",
                "-c",
                "/etc/patroni/config.yml",
                "failover",
                "moouro",
                "--primary",
                leader_node,
                "--candidate",
                follower_node,
                "--force",
            ],
        )

        # Wait for the promoted node to become leader
        new_leader_api_port = wait_for_patroni_leader(ip, timeout=90)
        new_leader_node = (
            "patroni1" if new_leader_api_port == api_ports["patroni1"] else "patroni2"
        )

        # Verify data survived the failover
        out = exec_patroni(
            new_leader_node,
            [
                "psql",
                "-U",
                "postgres",
                "-c",
                "SELECT value FROM patroni_test WHERE value = 'before_failover';",
            ],
        )
        assert "before_failover" in out
