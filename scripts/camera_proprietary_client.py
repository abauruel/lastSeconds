#!/usr/bin/env python3
"""Cliente para API proprietaria da camera (firmware P6S CGI).

Recursos:
- Login via /Security/UserAuthV2 (digest) com fallback para /Security/UserAuth
- Leitura de /System/DeviceInfo e /System/DeviceCap
- Zoom optico via /PTZ/{channel}/ZoomIn e /PTZ/{channel}/ZoomOut  (API P6S CGI)
- Foco via /PTZ/{channel}/FocusFar e /PTZ/{channel}/FocusNear
- Box zoom via /System/Device3DPositioningCfg

Uso rapido:
  python3 scripts/camera_proprietary_client.py --host 192.168.0.210 --user admin --password '' auth-test
  python3 scripts/camera_proprietary_client.py --host 192.168.0.210 --user admin --password '' zoom-in --speed 5 --seconds 2
  python3 scripts/camera_proprietary_client.py --host 192.168.0.210 --user admin --password '' zoom-out --speed 5 --seconds 2
  python3 scripts/camera_proprietary_client.py --host 192.168.0.210 --user admin --password '' focus-far --speed 5 --seconds 1
  python3 scripts/camera_proprietary_client.py --host 192.168.0.210 --user admin --password '' box --x0 480 --y0 270 --x1 1440 --y1 810
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional
import xml.etree.ElementTree as ET

import requests


def _build_nonce_b64() -> str:
    return base64.b64encode(os.urandom(16)).decode("ascii")


def _build_created_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _password_digest_b64(nonce_b64: str, created: str, password: str) -> str:
    raw = (nonce_b64 + created + password).encode("utf-8")
    sha1 = hashlib.sha1(raw).digest()
    return base64.b64encode(sha1).decode("ascii")


def _text(xml_root: ET.Element, tag_suffix: str) -> Optional[str]:
    for e in xml_root.iter():
        if e.tag.endswith("}" + tag_suffix) or e.tag == tag_suffix:
            return (e.text or "").strip()
    return None


@dataclass
class AuthResult:
    ok: bool
    method: str
    status_code: Optional[str]
    http_code: int
    message: str


class CameraClient:
    def __init__(self, host: str, user: str, password: str, channel: int = 1, timeout: int = 8):
        self.host = host
        self.base = f"http://{host}"
        self.user = user
        self.password = password
        self.channel = channel
        self.timeout = timeout
        self.session = requests.Session()
        self.session.verify = False
        requests.packages.urllib3.disable_warnings()  # type: ignore[attr-defined]

    def _auth(self):
        return (self.user, self.password) if self.user else None

    def _put_xml(self, path: str, xml_body: str) -> requests.Response:
        return self.session.put(
            self.base + path,
            data=xml_body.encode("utf-8"),
            headers={"Content-Type": "application/xml"},
            timeout=self.timeout,
            auth=self._auth(),
        )

    def _put_form(self, path: str, form_body: str) -> requests.Response:
        return self.session.put(
            self.base + path,
            data=form_body,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=self.timeout,
            auth=self._auth(),
        )

    def _get(self, path: str) -> requests.Response:
        return self.session.get(self.base + path, timeout=self.timeout, auth=self._auth())

    # ------------------------------------------------------------------ auth

    def auth_v2(self) -> AuthResult:
        nonce = _build_nonce_b64()
        created = _build_created_iso()
        digest = _password_digest_b64(nonce, created, self.password)
        payload = (
            "<?xml version='1.0' encoding='UTF-8'?>"
            "<Security>"
            f"<Username>{self.user}</Username>"
            f"<Password>{digest}</Password>"
            f"<Nonce>{nonce}</Nonce>"
            f"<Created>{created}</Created>"
            "</Security>"
        )
        resp = self._put_xml("/Security/UserAuthV2", payload)
        code = None
        msg = ""
        if resp.text:
            try:
                root = ET.fromstring(resp.text)
                code = _text(root, "statusCode")
                msg = _text(root, "message") or ""
            except ET.ParseError:
                msg = "Resposta nao-XML"
        ok = resp.status_code == 200 and code == "0"
        return AuthResult(ok=ok, method="UserAuthV2", status_code=code, http_code=resp.status_code, message=msg)

    def auth_v1(self) -> AuthResult:
        body = f"Username={self.user}&Password={self.password}"
        resp = self._put_form("/Security/UserAuth", body)
        code = None
        msg = ""
        if resp.text:
            try:
                root = ET.fromstring(resp.text)
                code = _text(root, "statusCode")
                msg = _text(root, "message") or ""
            except ET.ParseError:
                msg = "Resposta nao-XML"
        ok = resp.status_code == 200 and code == "0"
        return AuthResult(ok=ok, method="UserAuth", status_code=code, http_code=resp.status_code, message=msg)

    def login(self) -> AuthResult:
        v2 = self.auth_v2()
        if v2.ok:
            return v2
        v1 = self.auth_v1()
        if v1.ok:
            return v1
        merged_msg = (
            f"UserAuthV2 falhou (http={v2.http_code}, statusCode={v2.status_code}, msg={v2.message}); "
            f"UserAuth falhou (http={v1.http_code}, statusCode={v1.status_code}, msg={v1.message})"
        )
        return AuthResult(ok=False, method="none", status_code=v1.status_code, http_code=v1.http_code, message=merged_msg)

    # ------------------------------------------------------------------ PTZ motor (P6S CGI)

    def _ptz_cmd(self, action: str, start: bool, speed: int) -> requests.Response:
        """Envia comando PTZ motor via API P6S CGI.

        action: ZoomIn | ZoomOut | FocusFar | FocusNear
        start: True = iniciar movimento, False = parar
        speed: 1-10
        """
        path = f"/PTZ/{self.channel}/{action}"
        body = f"Param1={'1' if start else '0'}&Param2={speed}"
        resp = self._put_form(path, body)
        if resp.status_code == 401:
            raise PermissionError(
                f"HTTP 401 em {path}: credenciais CGI incorretas. "
                "Use --password com a senha da interface web da camera (pode ser vazia)."
            )
        return resp

    def zoom_in(self, speed: int = 5, seconds: float = 0) -> None:
        """Zoom in optico. Se seconds > 0, move por esse tempo e para."""
        r = self._ptz_cmd("ZoomIn", start=True, speed=speed)
        print(f"ZoomIn start  HTTP:{r.status_code}  statusCode:{_status_code_from(r)}")
        if seconds > 0:
            time.sleep(seconds)
            r2 = self._ptz_cmd("ZoomIn", start=False, speed=speed)
            print(f"ZoomIn stop   HTTP:{r2.status_code}  statusCode:{_status_code_from(r2)}")

    def zoom_out(self, speed: int = 5, seconds: float = 0) -> None:
        """Zoom out optico. Se seconds > 0, move por esse tempo e para."""
        r = self._ptz_cmd("ZoomOut", start=True, speed=speed)
        print(f"ZoomOut start HTTP:{r.status_code}  statusCode:{_status_code_from(r)}")
        if seconds > 0:
            time.sleep(seconds)
            r2 = self._ptz_cmd("ZoomOut", start=False, speed=speed)
            print(f"ZoomOut stop  HTTP:{r2.status_code}  statusCode:{_status_code_from(r2)}")

    def focus_far(self, speed: int = 5, seconds: float = 0) -> None:
        r = self._ptz_cmd("FocusFar", start=True, speed=speed)
        print(f"FocusFar start HTTP:{r.status_code}  statusCode:{_status_code_from(r)}")
        if seconds > 0:
            time.sleep(seconds)
            r2 = self._ptz_cmd("FocusFar", start=False, speed=speed)
            print(f"FocusFar stop  HTTP:{r2.status_code}  statusCode:{_status_code_from(r2)}")

    def focus_near(self, speed: int = 5, seconds: float = 0) -> None:
        r = self._ptz_cmd("FocusNear", start=True, speed=speed)
        print(f"FocusNear start HTTP:{r.status_code}  statusCode:{_status_code_from(r)}")
        if seconds > 0:
            time.sleep(seconds)
            r2 = self._ptz_cmd("FocusNear", start=False, speed=speed)
            print(f"FocusNear stop  HTTP:{r2.status_code}  statusCode:{_status_code_from(r2)}")

    # ------------------------------------------------------------------ zoom-to (posicao absoluta)

    # Calibracao: speed=10, ~0.4s por nivel de zoom (medido: 2s = 5 niveis)
    SECONDS_PER_LEVEL = 0.4
    ZOOM_MIN = 1
    ZOOM_MAX = 10
    RESET_SECONDS = 4.0  # tempo suficiente para ir de qualquer posicao ate 1x

    def zoom_reset(self, speed: int = 10) -> None:
        """Zoom out completo — leva a lente ao minimo (1x/wide)."""
        print(f"Zoom reset: zoom out por {self.RESET_SECONDS}s...")
        self._ptz_cmd("ZoomOut", start=True, speed=speed)
        time.sleep(self.RESET_SECONDS)
        self._ptz_cmd("ZoomOut", start=False, speed=speed)
        print("Zoom: 1x (minimo)")

    def zoom_to(self, level: int, speed: int = 10, seconds_per_level: float = SECONDS_PER_LEVEL) -> None:
        """Move a lente para o nivel de zoom absoluto (1x-10x).

        Estrategia:
          1. Zoom out completo (reset para 1x)
          2. Zoom in pelo numero de niveis desejado
        """
        level = max(self.ZOOM_MIN, min(self.ZOOM_MAX, level))
        print(f"Resetando para 1x (zoom out {self.RESET_SECONDS}s)...")
        self._ptz_cmd("ZoomOut", start=True, speed=speed)
        time.sleep(self.RESET_SECONDS)
        self._ptz_cmd("ZoomOut", start=False, speed=speed)
        time.sleep(0.1)

        if level > 1:
            steps = level - 1
            duration = steps * seconds_per_level
            print(f"Zoom in para {level}x ({steps} niveis, {duration:.2f}s)...")
            self._ptz_cmd("ZoomIn", start=True, speed=speed)
            time.sleep(duration)
            self._ptz_cmd("ZoomIn", start=False, speed=speed)

        print(f"Zoom: {level}x")

    # ------------------------------------------------------------------ Device3DPositioningCfg

    def put_3d_positioning(self, operator: int, x0: int, y0: int, x1: int, y1: int) -> requests.Response:
        cx = (x0 + x1) // 2
        cy = (y0 + y1) // 2
        xml = (
            "<?xml version='1.0' encoding='UTF-8' ?>"
            "<Device3DPositioningCfg>"
            f"<Operator>{operator}</Operator>"
            "<_3DPositionCoord>"
            f"<PointLeftTop><PosX>{x0}</PosX><PosY>{y0}</PosY></PointLeftTop>"
            f"<PointRightTop><PosX>{x1}</PosX><PosY>{y0}</PosY></PointRightTop>"
            f"<PointRightBottom><PosX>{x0}</PosX><PosY>{y1}</PosY></PointRightBottom>"
            f"<PointLeftBottom><PosX>{x1}</PosX><PosY>{y1}</PosY></PointLeftBottom>"
            f"<PointCenter><PosX>{cx}</PosX><PosY>{cy}</PosY></PointCenter>"
            "</_3DPositionCoord>"
            "</Device3DPositioningCfg>"
        )
        return self._put_xml("/System/Device3DPositioningCfg", xml)

    # ------------------------------------------------------------------ info

    def get_device_info(self) -> dict:
        r = self._get("/System/DeviceInfo")
        if r.status_code != 200:
            raise RuntimeError(f"GET /System/DeviceInfo retornou HTTP {r.status_code}")
        root = ET.fromstring(r.text)
        return {
            "DeviceName": _text(root, "DeviceName"),
            "Model": _text(root, "Model"),
            "SerialNumber": _text(root, "SerialNumber"),
            "SoftwareVersion": _text(root, "SoftwareVersion"),
        }

    def get_device_cap(self) -> str:
        r = self._get("/System/DeviceCap")
        if r.status_code != 200:
            raise RuntimeError(f"GET /System/DeviceCap retornou HTTP {r.status_code}")
        return r.text


def _status_code_from(resp: requests.Response) -> Optional[str]:
    try:
        root = ET.fromstring(resp.text)
        return _text(root, "statusCode")
    except Exception:
        return None


# ------------------------------------------------------------------ CLI

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Cliente API proprietaria da camera (P6S CGI)")
    p.add_argument("--host", required=True, help="IP/host da camera")
    p.add_argument("--user", required=True, help="Usuario web da camera")
    p.add_argument("--password", required=True, help="Senha web da camera")
    p.add_argument("--channel", type=int, default=1, help="Canal PTZ (default: 1)")
    p.add_argument("--timeout", type=int, default=8, help="Timeout HTTP em segundos")

    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("auth-test", help="Testa autenticacao UserAuthV2/UserAuth")
    sub.add_parser("device-info", help="Le DeviceInfo")
    sub.add_parser("device-cap", help="Le DeviceCap (XML bruto)")

    for cmd in ("zoom-in", "zoom-out", "focus-far", "focus-near"):
        sp = sub.add_parser(cmd, help=f"Motor: {cmd} (--seconds 0 = continuo ate Ctrl+C)")
        sp.add_argument("--speed", type=int, default=5, choices=range(1, 11), metavar="1-10")
        sp.add_argument("--seconds", type=float, default=2.0,
                        help="Duração em segundos (0 = start e para manualmente com Ctrl+C)")

    reset_sp = sub.add_parser("reset", help="Zoom out completo: leva a lente ao minimo (1x)")
    reset_sp.add_argument("--speed", type=int, default=10, choices=range(1, 11), metavar="1-10")

    zoom_to_sp = sub.add_parser("zoom-to", help="Zoom absoluto 1x-10x (reset + move)")
    zoom_to_sp.add_argument("--level", type=int, required=True, choices=range(1, 11), metavar="1-10",
                            help="Nivel de zoom alvo (1=wide, 10=tele)")
    zoom_to_sp.add_argument("--speed", type=int, default=10, choices=range(1, 11), metavar="1-10")
    zoom_to_sp.add_argument("--spl", type=float, default=CameraClient.SECONDS_PER_LEVEL,
                            help=f"Segundos por nivel (default: {CameraClient.SECONDS_PER_LEVEL})")

    click_sp = sub.add_parser("click", help="3D click (operator=0)")
    click_sp.add_argument("--x", type=int, required=True)
    click_sp.add_argument("--y", type=int, required=True)

    box_sp = sub.add_parser("box", help="3D box zoom (operator=1)")
    box_sp.add_argument("--x0", type=int, required=True)
    box_sp.add_argument("--y0", type=int, required=True)
    box_sp.add_argument("--x1", type=int, required=True)
    box_sp.add_argument("--y1", type=int, required=True)

    return p


def main() -> None:
    args = _build_parser().parse_args()
    client = CameraClient(
        host=args.host,
        user=args.user,
        password=args.password,
        channel=getattr(args, "channel", 1),
        timeout=getattr(args, "timeout", 8),
    )

    # Autenticar primeiro (exceto auth-test que faz o proprio teste)
    if args.command != "auth-test":
        result = client.login()
        if not result.ok:
            print(f"Falha na autenticacao: {result.message}", file=sys.stderr)
            sys.exit(1)

    if args.command == "auth-test":
        result = client.login()
        if result.ok:
            print(f"Autenticado com sucesso via {result.method}")
        else:
            print(f"Falha: {result.message}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "device-info":
        info = client.get_device_info()
        for k, v in info.items():
            print(f"{k}: {v}")

    elif args.command == "device-cap":
        print(client.get_device_cap())

    elif args.command == "zoom-in":
        if args.seconds == 0:
            print("ZoomIn continuo — pressione Ctrl+C para parar")
            client._ptz_cmd("ZoomIn", start=True, speed=args.speed)
            try:
                while True:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                client._ptz_cmd("ZoomIn", start=False, speed=args.speed)
                print("\nParado.")
        else:
            client.zoom_in(speed=args.speed, seconds=args.seconds)

    elif args.command == "zoom-out":
        if args.seconds == 0:
            print("ZoomOut continuo — pressione Ctrl+C para parar")
            client._ptz_cmd("ZoomOut", start=True, speed=args.speed)
            try:
                while True:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                client._ptz_cmd("ZoomOut", start=False, speed=args.speed)
                print("\nParado.")
        else:
            client.zoom_out(speed=args.speed, seconds=args.seconds)

    elif args.command == "focus-far":
        if args.seconds == 0:
            print("FocusFar continuo — pressione Ctrl+C para parar")
            client._ptz_cmd("FocusFar", start=True, speed=args.speed)
            try:
                while True:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                client._ptz_cmd("FocusFar", start=False, speed=args.speed)
                print("\nParado.")
        else:
            client.focus_far(speed=args.speed, seconds=args.seconds)

    elif args.command == "focus-near":
        if args.seconds == 0:
            print("FocusNear continuo — pressione Ctrl+C para parar")
            client._ptz_cmd("FocusNear", start=True, speed=args.speed)
            try:
                while True:
                    time.sleep(0.5)
            except KeyboardInterrupt:
                client._ptz_cmd("FocusNear", start=False, speed=args.speed)
                print("\nParado.")
        else:
            client.focus_near(speed=args.speed, seconds=args.seconds)

    elif args.command == "reset":
        client.zoom_reset(speed=args.speed)

    elif args.command == "zoom-to":
        client.zoom_to(level=args.level, speed=args.speed, seconds_per_level=args.spl)

    elif args.command == "click":
        r = client.put_3d_positioning(0, args.x, args.y, args.x, args.y)
        print(f"HTTP: {r.status_code}\n{r.text}")

    elif args.command == "box":
        r = client.put_3d_positioning(1, args.x0, args.y0, args.x1, args.y1)
        print(f"HTTP: {r.status_code}\n{r.text}")


if __name__ == "__main__":
    main()
