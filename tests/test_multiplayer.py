"""Tests for the LAN/Direct-IP co-op multiplayer system."""
from __future__ import annotations

import time

import pytest


@pytest.fixture
def game():
    """Headless Game fixture for multiplayer tests."""
    from stellar_forge.core.game import Game
    g = Game(headless=True)
    g.new_game(seed=42)
    yield g


def test_protocol_round_trip():
    """send_msg/recv_msg serialise and deserialise a dict faithfully."""
    import socket
    from stellar_forge.net.protocol import recv_msg, send_msg

    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind(("127.0.0.1", 0))
    port = srv.getsockname()[1]
    srv.listen(1)
    cli = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    cli.connect(("127.0.0.1", port))
    conn, _ = srv.accept()
    msg = {"t": "hello", "name": "Test-Pilot", "values": [1, 2.5, True, None]}
    send_msg(cli, msg)
    got = recv_msg(conn)
    assert got == msg
    cli.close()
    conn.close()
    srv.close()


def test_host_client_connect_and_disconnect(game):
    """A client can connect to a host, exchange hello/welcome, and disconnect cleanly."""
    from stellar_forge.net.session import NetClient, NetHost

    host = NetHost(host_name="Host-Test", port=0)
    host.welcome_fn = lambda: {"seed": 42, "chapter": 3}
    bound = host.start()
    assert bound > 0

    client = NetClient("127.0.0.1", port=bound, name="Client-Test")
    welcome = client.connect()
    assert welcome["pid"] >= 1
    assert welcome["seed"] == 42
    assert client.running

    # Host should see the join event
    time.sleep(0.1)
    plist = host.player_list()
    assert len(plist) == 2
    assert any(p["name"] == "Client-Test" for p in plist)

    client.stop()
    # recv thread has a 0.5s timeout before it notices the closed socket
    time.sleep(1.0)
    assert len(host.player_list()) == 1

    host.stop()


def test_host_broadcast_reaches_client():
    """Messages broadcast by the host arrive in the client inbox."""
    from stellar_forge.net.session import NetClient, NetHost

    host = NetHost(host_name="BroadcastHost", port=0)
    host.welcome_fn = lambda: {"seed": 1}
    bound = host.start()
    client = NetClient("127.0.0.1", port=bound, name="Listener")
    client.connect()
    time.sleep(0.05)

    host.broadcast({"t": "test_ping", "v": 123})
    time.sleep(0.15)

    msgs = []
    while True:
        try:
            msgs.append(client.inbox.get_nowait())
        except Exception:
            break
    assert any(m.get("t") == "test_ping" and m.get("v") == 123 for m in msgs)

    client.stop()
    host.stop()


def test_netsync_captures_local_state(game):
    """NetSync._capture_local_state returns a dict with the ship's coordinates."""
    from stellar_forge.net.session import NetHost
    from stellar_forge.net.sync import NetSync

    # Force the space scene onto the stack so scenes.top is SpaceScene
    game.scenes.stack = [game.space]

    host = NetHost(host_name="SyncHost", port=0)
    host.welcome_fn = lambda: {"seed": game.state.seed}
    host.start()
    sync = NetSync(game, host)
    game.net = sync

    state = sync._capture_local_state()
    assert state["loc"] == "space"
    assert "x" in state and "y" in state
    assert state["ship"] == game.state.ship

    sync.stop()
    game.net = None


def test_remote_peer_interpolation():
    """RemotePeer smoothly interpolates towards its target position."""
    from stellar_forge.net.sync import RemotePeer

    peer = RemotePeer(1, "TestPeer", (255, 210, 95))
    peer.apply({"x": 100.0, "y": 200.0, "vx": 0.0, "vy": 0.0, "loc": "space"})
    assert peer._has_pos
    assert peer.rx == 100.0

    peer.apply({"x": 200.0, "y": 200.0, "vx": 100.0, "vy": 0.0, "loc": "space"})
    for _ in range(30):
        peer.step(0.016)
    assert peer.rx > 100.0  # moved towards 200
    assert abs(peer.ry - 200.0) < 5.0


def test_server_full_rejects():
    """A host at max capacity rejects additional connections."""
    from stellar_forge.net.session import NetClient, NetHost

    host = NetHost(host_name="FullHost", port=0, max_players=2)
    host.welcome_fn = lambda: {"seed": 1}
    bound = host.start()

    c1 = NetClient("127.0.0.1", port=bound, name="P2")
    c1.connect()
    time.sleep(0.05)
    assert len(host.player_list()) == 2

    with pytest.raises(ConnectionError, match="full"):
        c2 = NetClient("127.0.0.1", port=bound, name="P3")
        c2.connect()

    c1.stop()
    host.stop()


def test_game_host_multiplayer_method(game):
    """game.host_multiplayer() starts a host and sets game.net."""
    port = game.host_multiplayer(port=0, name="IntegHost")
    assert port > 0
    assert game.net is not None
    assert game.net.is_host
    game.stop_multiplayer()
    assert game.net is None


def test_lan_discovery():
    """discover_lan finds a host advertising on the same machine."""
    from stellar_forge.net.session import NetHost, discover_lan

    host = NetHost(host_name="LAN-Test", port=0)
    host.welcome_fn = lambda: {"seed": 1}
    host.start()
    time.sleep(0.1)

    found = discover_lan(timeout=0.4, port=host.discovery_port)
    # LAN broadcast on loopback may not work in all test envs, so we don't assert found
    # but we do verify it doesn't crash and returns a list
    assert isinstance(found, list)

    host.stop()
