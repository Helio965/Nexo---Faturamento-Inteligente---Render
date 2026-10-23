"""SEC-006B: instalador fixo e verificado antes dos requisitos do NEXO.

Somente stdlib; não importa a aplicação nem lê .env. O pip preexistente nunca
processa os requisitos ou o wheel de bootstrap. Proxy/TLS do sistema permanecem
ativos. Execute com o Python do ambiente de destino (virtualenv no uso local).
"""

import argparse
import hashlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parents[1]
PIP_VERSION = "26.2.2"
PIP_WHEEL = "pip-26.2.2-py3-none-any.whl"
PIP_URL = (
    "https://files.pythonhosted.org/packages/3f/06/"
    "3e4420302363fbb71be3c7f35ce042f54bfca330e3e66b3a2e3c4cca579f/"
    + PIP_WHEEL
)
PIP_SHA256 = "fd7f4dfa8190e014013b9f08f3e973f4e4c26ffd179a204895533a7254813a70"
PYPI_INDEX = "https://pypi.org/simple"
MAX_WHEEL_BYTES = 16 * 1024 * 1024
SAFE_ENVIRONMENT = {
    "PATH", "HOME", "USERPROFILE", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT",
    "TEMP", "TMP", "TMPDIR", "LANG", "LC_ALL", "LC_CTYPE", "VIRTUAL_ENV",
    "LD_LIBRARY_PATH", "DYLD_LIBRARY_PATH", "SSL_CERT_FILE", "SSL_CERT_DIR",
    "REQUESTS_CA_BUNDLE", "CURL_CA_BUNDLE", "HTTP_PROXY", "HTTPS_PROXY",
    "ALL_PROXY", "NO_PROXY", "http_proxy", "https_proxy", "all_proxy", "no_proxy",
}


class BootstrapError(RuntimeError):
    pass


class OfficialWheelRedirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urllib.parse.urlsplit(newurl)
        if (target.scheme != "https" or target.hostname != "files.pythonhosted.org"
                or target.port not in {None, 443} or target.username or target.password):
            raise BootstrapError("Redirecionamento fora da origem HTTPS oficial recusado.")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download_verified_wheel(directory):
    destination = Path(directory) / PIP_WHEEL
    opener = urllib.request.build_opener(OfficialWheelRedirects())
    digest = hashlib.sha256()
    size = 0
    with opener.open(PIP_URL, timeout=30) as response, destination.open("wb") as output:
        while chunk := response.read(64 * 1024):
            size += len(chunk)
            if size > MAX_WHEEL_BYTES:
                raise BootstrapError("Wheel do instalador excede o limite esperado.")
            digest.update(chunk)
            output.write(chunk)
    if digest.hexdigest() != PIP_SHA256:
        raise BootstrapError("SHA256 do instalador não confere; instalação interrompida.")
    return destination


def installer_environment(empty_netrc):
    # Não propagar segredos da aplicação, índices, certificados desativados,
    # PYTHONPATH ou configuração pip herdada aos processos de instalação.
    environment = {key: value for key, value in os.environ.items() if key in SAFE_ENVIRONMENT}
    environment.update(PIP_CONFIG_FILE=os.devnull, NETRC=str(empty_netrc),
                       PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1")
    return environment


def verify_installed_pip(environment):
    probe = (
        "import importlib.metadata, pip; "
        "actual=importlib.metadata.version('pip'); "
        f"assert actual == {PIP_VERSION!r}; "
        f"assert pip.__version__ == {PIP_VERSION!r}; "
        "print('pip=' + actual)"
    )
    result = subprocess.run([sys.executable, "-I", "-B", "-c", probe], cwd=ROOT,
                            env=environment, capture_output=True, text=True, check=False)
    if result.returncode:
        raise BootstrapError("Versão efetiva do pip não confirmada; requisitos não instalados.")
    print(result.stdout.strip(), flush=True)


def install(requirements="requirements.txt", *, prepare_only=False, report=None):
    if requirements not in {"requirements.txt", "requirements-dev.txt"}:
        raise BootstrapError("Arquivo de requisitos não permitido.")
    with tempfile.TemporaryDirectory(prefix="nexo-verified-installer-") as temporary:
        wheel = download_verified_wheel(temporary)
        netrc = Path(temporary) / "empty-netrc"
        netrc.touch(mode=0o600)
        environment = installer_environment(netrc)
        # Executa o pip corrigido diretamente do wheel com hash já validado.
        # -I ignora user site/PYTHONPATH; não usar -S (preserva prefix da venv).
        launcher = (
            "import runpy,sys; wheel=sys.argv.pop(1); "
            "sys.path.insert(0,wheel); runpy.run_module('pip',run_name='__main__')"
        )
        common = ["--isolated", "--disable-pip-version-check", "--no-cache-dir", "--no-input"]
        subprocess.run(
            [sys.executable, "-I", "-B", "-c", launcher, str(wheel), *common,
             "install", "--no-index", "--no-deps", "--force-reinstall", str(wheel)],
            cwd=ROOT, env=environment, check=True,
        )
        verify_installed_pip(environment)
        if prepare_only:
            return
        command = [sys.executable, "-I", "-B", "-m", "pip", *common, "install",
                   "--index-url", PYPI_INDEX, "--keyring-provider", "disabled",
                   "-r", str(ROOT / requirements)]
        if report is not None:
            command.extend(["--report", str(Path(report).resolve())])
        subprocess.run(command, cwd=ROOT, env=environment, check=True)
        subprocess.run([sys.executable, "-I", "-B", "-m", "pip", *common, "check"],
                       cwd=ROOT, env=environment, check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", choices=("requirements.txt", "requirements-dev.txt"),
                        default="requirements.txt")
    parser.add_argument("--prepare-only", action="store_true")
    parser.add_argument("--report", type=Path, help="Relatório JSON pip, fora do Git.")
    args = parser.parse_args()
    try:
        install(args.requirements, prepare_only=args.prepare_only, report=args.report)
    except BootstrapError as error:
        parser.exit(1, str(error) + "\n")
    except (OSError, subprocess.CalledProcessError):
        # Não incluir exceções de rede/env, que podem conter URLs de proxy.
        parser.exit(1, "Preparação/instalação segura falhou; nenhuma etapa posterior foi executada.\n")


if __name__ == "__main__":
    main()
