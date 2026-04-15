# Copyright  Alexandre Díaz <dev@redneboa.es>
import os
import time
import pytest
import shutil
import subprocess
from pathlib import Path
from python_on_whales import DockerClient

IMAGE_TAG_NAME = "localhost/test:docker-moouro"
COMPOSE_PROJECT_NAME = "moouro-test"
ODOO_VERSIONS = {
    "9.6": "8.0",
    "10": "13.0",
    "11": "13.0",
    "12": "18.0",
    "13": "19.0",
    "14": "19.0",
    "15": "19.0",
    "16": "19.0",
    "17": "19.0",
    "18": "19.0",
}
PG_CONFIGS = {
    "9.6": "9.6.postgresql.conf",
    "10": "10.postgresql.conf",
    "11": "10.postgresql.conf",
    "12": "10.postgresql.conf",
    "13": "13.postgresql.conf",
    "14": "13.postgresql.conf",
    "15": "13.postgresql.conf",
    "16": "13.postgresql.conf",
    "17": "13.postgresql.conf",
    "18": "13.postgresql.conf",
}
OLDER_VERSIONS = ("8.0",)


def _compose_raw(
    client: str, command: list[str], check: bool = False, stdin: str = None
) -> str:
    podman_cmd = [client, "compose", "-p", COMPOSE_PROJECT_NAME]

    podman_cmd.extend(command)

    result = subprocess.run(
        podman_cmd,
        input=stdin,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=check,
    )

    output = result.stdout

    clean_lines = [
        line
        for line in output.splitlines(keepends=True)
        if "The input device is not a TTY" not in line
    ]
    clean_output = "".join(clean_lines)

    return clean_output


def _podman_build(
    context_path,
    file=None,
    tags=None,
    cache=True,
    pull=True,
    build_args=None,
    extra_args=None,
):
    context_path = Path(context_path).resolve()
    if not context_path.is_dir():
        raise ValueError(f"Context path is not a valid directory: {context_path}")

    cmd = ["podman", "build", "--format", "docker"]

    if file:
        cmd.extend(["-f", str(Path(file).resolve())])

    if tags:
        if isinstance(tags, str):
            tags = [tags]
        for tag in tags:
            cmd.extend(["-t", tag])
    if not cache:
        cmd.append("--no-cache")
    if pull:
        cmd.append("--pull")

    if build_args:
        if isinstance(build_args, dict):
            for key, value in build_args.items():
                cmd.extend(["--build-arg", f"{key}={value}"])
        elif isinstance(build_args, str):
            cmd.extend(["--build-arg", build_args])
        else:
            for arg in build_args:
                cmd.extend(["--build-arg", str(arg)])

    if extra_args:
        cmd.extend(extra_args)

    cmd.append(str(context_path))

    try:
        subprocess.run(
            cmd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
    except subprocess.CalledProcessError as e:
        print("Error podman build:")
        print(e.output if e.output else "No detailed output.")
        raise


def _get_preferred_client_type():
    if shutil.which("podman"):
        return "podman"
    if shutil.which("docker"):
        return "docker"
    raise RuntimeError("Need install podman or docker (with compose)")


def wait_for_odoo(ip_address, port):
    import requests
    from requests.exceptions import RequestException

    url = f"http://{ip_address}:{port}"
    for _ in range(300):
        try:
            r = requests.get(url, timeout=5)
            if r.status_code == 200:
                break
        except RequestException:
            pass
        time.sleep(2)
    else:
        raise TimeoutError("Odoo did not start on time")
    time.sleep(5)  # Wait for pgBackRest and resticprofile


def project_compose_up(client_type, docker):
    if client_type == "podman":
        subprocess.Popen(
            ["podman", "compose", "-p", COMPOSE_PROJECT_NAME, "up", "--remove-orphans"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    else:
        docker.compose.up(
            detach=True,
            remove_orphans=True,
        )


def pytest_addoption(parser):
    parser.addoption("--no-cache", action="store_true", default=False)
    parser.addoption("--pg-version", action="store", default="9.6")
    parser.addoption("--client-type", action="store", default=None)


@pytest.fixture(scope="session")
def env_info(pytestconfig):
    no_cache = bool(pytestconfig.getoption("no_cache", False))
    pg_ver = pytestconfig.getoption("pg_version")
    client_type = pytestconfig.getoption("client_type") or _get_preferred_client_type()
    odoo_ver = ODOO_VERSIONS.get(pg_ver)

    return {
        "ip": "127.0.0.1",
        "ports": {
            "psql": "5433",
            "odoo": "8069",
        },
        "options": {
            "no_cache": no_cache,
            "pg_version": pg_ver,
            "odoo_version": odoo_ver,
        },
        "client_type": client_type,
    }


@pytest.fixture(scope="session")
def docker_env(env_info):
    odoo_ver = env_info["options"]["odoo_version"]
    pg_ver = env_info["options"]["pg_version"]
    os.environ["PYTEST_ODOO_VERSION"] = odoo_ver
    os.environ["PYTEST_PG_VERSION"] = pg_ver
    os.environ["PYTEST_PG_DATA"] = (
        f"/var/lib/postgresql/{pg_ver}/docker"
        if float(pg_ver) >= 18
        else "/var/lib/postgresql/data"
    )
    os.environ["PYTEST_PG_DATA_VOLUME"] = (
        f"/var/lib/postgresql" if float(pg_ver) >= 18 else "/var/lib/postgresql/data"
    )
    os.environ["PYTEST_PG_CONFIG"] = PG_CONFIGS[pg_ver]
    client_type = env_info["client_type"]
    client_call = [client_type]
    dockerfile = f"{pg_ver}.Dockerfile"

    # Generate pgBackRest Configuration
    with open("./tests/data/project_demo/config/pgbackrest.conf.tmpl") as f:
        pgbakcrest_content = os.path.expandvars(f.read())
    with open("./tests/data/project_demo/config/pgbackrest.conf", "w") as f:
        f.write(pgbakcrest_content)

    # Moouro Base
    if client_type == "podman":
        os.environ["PODMAN_COMPOSE_PROVIDER"] = "/usr/bin/podman-compose"
        os.environ["PODMAN_COMPOSE_WARNING_LOGS"] = "false"
        _podman_build(
            ".",
            file=dockerfile,
            tags=f"{IMAGE_TAG_NAME}-{pg_ver}",
            cache=not env_info["options"]["no_cache"],
        )
    else:
        docker = DockerClient(client_call=client_call, client_type=client_type)
        docker.build(
            ".",
            file=dockerfile,
            tags=f"{IMAGE_TAG_NAME}-{pg_ver}",
            cache=not env_info["options"]["no_cache"],
        )

    os.chdir("./tests/data/project_demo")

    # isOdoo Runtime
    if client_type == "podman":
        _podman_build(
            ".",
            file=f"./Dockerfile",
            tags=f"{IMAGE_TAG_NAME}-odoo-{pg_ver}",
            cache=not env_info["options"]["no_cache"],
            build_args={
                "ODOO_VERSION": odoo_ver,
            },
            extra_args=[
                "--build-context",
                "deps=./deps",
                "--build-context",
                "addons=./addons",
            ],
        )
    else:
        docker = DockerClient(client_call=client_call, client_type=client_type)
        docker.build(
            ".",
            file=f"./Dockerfile",
            tags=f"{IMAGE_TAG_NAME}-odoo-{pg_ver}",
            cache=not env_info["options"]["no_cache"],
            build_args={
                "ODOO_VERSION": odoo_ver,
            },
            build_contexts={
                "deps": "./deps",
                "addons": "./addons",
            },
        )

    docker = DockerClient(
        client_call=client_call,
        client_type=client_type,
        compose_files=["docker-compose.yaml"],
        compose_project_name=COMPOSE_PROJECT_NAME,
    )

    init_params = [
        "odoo",
        "-i",
        "base",
        "--stop-after-init",
        "--no-xmlrpc" if odoo_ver in OLDER_VERSIONS else "--no-http",
    ]
    try:
        # Initialize Database
        if client_type == "podman":
            subprocess.run(
                [
                    "podman",
                    "compose",
                    "-p",
                    COMPOSE_PROJECT_NAME,
                    "run",
                    "--rm",
                    "odoo",
                ]
                + init_params,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60,
                check=True,
            )
        else:
            docker.compose.run(
                "odoo",
                init_params,
                remove=True,
            )

        # Up Services
        print("Waiting Odoo...")
        project_compose_up(client_type, docker)
        wait_for_odoo(env_info["ip"], env_info["ports"]["odoo"])

        yield docker
    finally:
        print("===== DB LOGS")
        print(docker.compose.logs("db"))
        docker.compose.down(remove_orphans=True, volumes=True)


@pytest.fixture(scope="session")
def exec_docker_db(env_info):
    def _run(args: list[str], stdin=None) -> str:
        client_type = env_info["client_type"]
        return _compose_raw(
            client_type, ["exec", "-u", "postgres", "db"] + args, stdin=stdin
        )

    return _run


@pytest.fixture(scope="session")
def run_docker_db(env_info):
    def _run(args: list[str], stdin=None):
        client_type = env_info["client_type"]
        return _compose_raw(
            client_type, ["run", "--rm", "-u", "postgres", "db"] + args, stdin=stdin
        )

    return _run


@pytest.fixture(scope="session")
def run_docker_db_no_entrypoint(env_info):
    def _run(args: list[str], stdin=None):
        args_str = " ".join(args)
        client_type = env_info["client_type"]
        return _compose_raw(
            client_type,
            [
                "run",
                "--rm",
                "--entrypoint",
                "/bin/sh",
                "-u",
                "postgres",
                "db",
                "-c",
                args_str,
            ],
            stdin=stdin,
        )

    return _run
