# Copyright  Alexandre Díaz <dev@redneboa.es>
import requests
import re


class TestMoouroContainer:
    def test_pg_version(self, exec_docker_db, env_info):
        version = exec_docker_db(["psql", "--version"])
        assert env_info["options"]["pg_version"] in version

    def test_pgbackrest_check(self, exec_docker_db, env_info):
        output = exec_docker_db(["pgbackrest", "--stanza=main", "check"])
        assert "check command end: completed successfully" in output.lower()

    def test_pgbackrest_backup(self, exec_docker_db):
        output = exec_docker_db(["pgbackrest", "--stanza=main", "backup"])
        assert "backup command end: completed successfully" in output.lower()

    # def test_pgbackrest_restore(self, exec_docker_db):
    #     # Hack: move pid
    #     exec_docker_db(["mv", "/var/lib/postgresql/data/postmaster.pid", "/var/lib/postgresql/data/bck-postmaster.pid"])
    #     output = exec_docker_db(["pgbackrest", "--stanza=main", "restore", "--delta", "--type=name", "--target=/tmp/pgbackrest_restore"])
    #     exec_docker_db(["mv", "/var/lib/postgresql/data/bck-postmaster.pid", "/var/lib/postgresql/data/postmaster.pid"])
    #     assert "restore command end: completed successfully" in output.lower()

    def test_resticprofile_check(self, exec_docker_db):
        output = exec_docker_db(["resticprofile", "check"])
        assert 'no errors were found' in output.lower()

    def test_resticprofile_backup(self, exec_docker_db):
        output = exec_docker_db(["resticprofile", "backup"])
        assert re.search(r'snapshot\s+\w+\s+saved', output.lower())

    def test_resticprofile_restore(self, exec_docker_db):
        output = exec_docker_db(["resticprofile", "restore", "--snapshot", "latest", "--target", "/tmp/restic_restore"])
        assert 'summary: restored' in output.lower()

    def test_moouro_check(self, exec_docker_db):
        output = exec_docker_db(["moouro_check"])
        assert "check command end: completed successfully" in output.lower() and 'no errors were found' in output.lower()

    def test_moouro_list(self, exec_docker_db):
        output = exec_docker_db(["moouro_list"])
        assert "database backup size" in output.lower() and "finished 'snapshots'" in output.lower()

    def test_moouro_backup(self, exec_docker_db):
        output = exec_docker_db(["moouro_backup"])
        assert "backup command end: completed successfully" in output.lower() and re.search(r'snapshot\s+\w+\s+saved', output.lower())
