import logging

from infrahub_sdk import InfrahubClient
from infrahub_sdk.exceptions import NodeNotFoundError

IXPS = [
    {
        "name": "IX-Denver",
        "description": "Denver Internet Exchange",
        "network": "203.0.114.0/24",
        "sites": ["den1"],
    },
    {
        "name": "AtlantaIX",
        "description": "Atlanta Internet Exchange",
        "network": "203.0.115.0/24",
        "sites": ["atl1"],
    },
]

IXP_PEERS = [
    {"name": "Cogent IX-Denver 1", "asn": 174, "ixp": "IX-Denver"},
    {"name": "Cogent IX-Denver 2", "asn": 174, "ixp": "IX-Denver"},
    {"name": "Cogent AtlantaIX 1", "asn": 174, "ixp": "AtlantaIX"},
    {"name": "Cogent AtlantaIX 2", "asn": 174, "ixp": "AtlantaIX"},
    {"name": "Tata IX-Denver 1", "asn": 6453, "ixp": "IX-Denver"},
    {"name": "Tata IX-Denver 2", "asn": 6453, "ixp": "IX-Denver"},
    {"name": "Tata AtlantaIX 1", "asn": 6453, "ixp": "AtlantaIX"},
    {"name": "Tata AtlantaIX 2", "asn": 6453, "ixp": "AtlantaIX"},
]

IXP_ENDPOINTS = [
    {"ixp": "IX-Denver", "device": "den1-edge1", "interface": "Ethernet7"},
    {"ixp": "IX-Denver", "device": "den1-edge2", "interface": "Ethernet7"},
    {"ixp": "AtlantaIX", "device": "atl1-edge1", "interface": "Ethernet7"},
    {"ixp": "AtlantaIX", "device": "atl1-edge2", "interface": "Ethernet7"},
    
]

async def run(client: InfrahubClient, log: logging.Logger, branch: str) -> None:
    await create_and_set_peer_group(client, log, branch)
    await create_ixps(client, log, branch)
    await create_ixp_peers(client, log, branch)
    await create_ixp_endpoints(client, log, branch)

    account = await client.create("CoreAccount", name="Generator", password="SomeComplexPw123", type="Script", role="read-write")
    await account.save()
    group = await client.create("CoreStandardGroup", name="ixp_bgp_private_peerings")
    await group.save()


async def create_and_set_peer_group(
    client: InfrahubClient, log: logging.Logger, branch: str
) -> None:
    asn = await client.get("InfraAutonomousSystem", asn__value=64496)
    peer_group = await client.create("InfraBGPPeerGroup", name="PEER_AMERICAS", import_policies="IMPORT_PEER_AMERICAS", export_policies="EXPORT_PEER_AMERICAS", local_as = asn)
    await peer_group.save()


    for continent in ["North America", "South America"]:
        location = await client.get("LocationContinent", name__value = continent)
        location.bgp_peer_group = peer_group
        await location.save()

    return


async def create_ixps(client: InfrahubClient, log: logging.Logger, branch: str) -> None:
    for ixp in IXPS:
        ixp_net = await client.create(
            kind="IpamIPPrefix", member_type="address", prefix=ixp.pop("network")
        )
        await ixp_net.save(allow_upsert=True)

        ixp_data = {
            "networks": [ixp_net]
        }

        pool = await client.create(
            kind="CoreIPAddressPool",
            default_address_type="IpamIPAddress",
            name=f"{ixp.get('name')} pool",
            default_prefix_length=32,
            resources=[ixp_net],
            is_pool=True,
            ip_namespace={"id": "default"},
        )
        await pool.save(allow_upsert=True)

        ixp_data["address_pool"] = pool.id

        if ixp.get("sites"):
            ixp_data["sites"] = await client.filters("LocationSite", name__values=ixp.get("sites"))

        obj = await client.create(
            kind="InfraIXP",
            branch=branch,
            data={
                **ixp,
                **ixp_data,
            },
        )
        await obj.save()
    return


async def create_ixp_peers(
    client: InfrahubClient, log: logging.Logger, branch: str
) -> None:
    for ixp_peer in IXP_PEERS:
        ixp = await client.get(
            "InfraIXP", branch=branch, name__value=ixp_peer.get("ixp")
        )

        await ixp.address_pool.fetch()

        asn = await client.get(
            "InfraAutonomousSystem", branch=branch, asn__value=ixp_peer.get("asn")
        )

        obj = await client.create(
            kind="InfraIXPPeer",
            branch=branch,
            ixp=ixp,
            data={
                **ixp_peer,
                **{"ipaddress": ixp.address_pool.peer, "asn": asn},
            },
        )
        await obj.save()
    return


async def create_ixp_endpoints(
    client: InfrahubClient, log: logging.Logger, branch: str
):
    for ixp_endpoint in IXP_ENDPOINTS:
        device = await client.get(
            "InfraDevice", branch=branch, name__value=ixp_endpoint.get("device")
        )
        ixp = await client.get("InfraIXP", name__value=ixp_endpoint.get("ixp"))

        await ixp.address_pool.fetch()

        interface = await client.get(
            "InfraInterface",
            branch=branch,
            name__value=ixp_endpoint.get("interface"),
            device__ids=[device.id],
        )

        interface.role.value = "peering"

        # assign IP address out of a pool
        await interface.ip_addresses.fetch()
        interface.ip_addresses.add(ixp.address_pool.peer)
        await interface.save()

        endpoint = await client.create(
            "InfraIXPEndpoint",
            data={
                "name": ixp_endpoint.get("name"),
                "ixp": ixp,
                "connected_endpoint": interface,
            },
        )
        await endpoint.save(allow_upsert=True)
