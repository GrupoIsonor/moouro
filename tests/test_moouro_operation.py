# Copyright  Alexandre Díaz <dev@redneboa.es>
import xmlrpc.client as xmlrpclib
import base64
import re
import json
from conftest import project_compose_up, wait_for_odoo


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
