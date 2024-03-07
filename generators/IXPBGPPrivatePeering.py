import asyncio
import logging
import os

from pathlib import Path
from typing import Union

from infrahub_sdk import Config, InfrahubClient, InfrahubNode, NodeNotFound


from utils import inherit_attribute_from_hierarchy, InheritanceException


async def run(client: InfrahubClient, log: logging.Logger, branch: str, **kwargs) -> None:
    if not "instance" in kwargs:
        raise ValueError("No instance provided")

    instance = kwargs["instance"]

    try:
        service = await client.get(
            "IxpIXPBGPPrivatePeering",
            branch=branch,
            name__value=instance,
            populate_store=True,
            prefetch_relationships=True,
        )
    except NodeNotFound:
        raise ValueError(f"IxpIXPBGPPrivatePeering instance {instance} not found in Infrahub")

    await service.asn.peer.organization.fetch()
    await service.ixp.peer.locations.fetch()

    try:
        peer_group = await inherit_attribute_from_hierarchy(
            client, service.ixp.peer.locations.peers[0].peer, "transit_peer_group"
        )
    except InheritanceException:
        peer_group = None

    ixp_peers = await client.filters(
        kind="InfraIXPPeer",
        branch=branch,
        asn__ids=[service.asn.id],
        ixp__ids=[service.ixp.id]
    )

    ixp_endpoints = await client.filters(
        kind="InfraIXPEndpoint",
        branch=branch,
        ixp__ids=[service.ixp.id]
    )

    if len(ixp_peers) != len(ixp_endpoints) and service.redundant.value:
        raise ValueError("Redundancy is required but the amount of IXP Peers does not match the amount the amount of endpoints")

    if not service.redundant.value:
        ixp_peers = [ixp_peers[0]]
        ixp_endpoints = [ixp_endpoints[0]]

    local_asn = await client.get(
        "InfraAutonomousSystem", branch=branch, asn__value=64511
    )

    try:
        account = await client.get("CoreAccount", name__value="Generator")
    except NodeNotFound:
        raise ValueError("Unable to find CoreAccount Generator in Infrahub")

    async with client.start_tracking(identifier=Path(__file__).stem, params={"name": instance}, delete_unused_nodes=True) as client:
        for idx, (ixp_peer, ixp_endpoint) in enumerate(zip(ixp_peers, ixp_endpoints), start=1):

            await ixp_peer.ipaddress.fetch()

            await ixp_endpoint.connected_endpoint.fetch()
            await ixp_endpoint.connected_endpoint.peer.ip_addresses.fetch()
            await ixp_endpoint.connected_endpoint.peer.device.fetch()

            org_slug = service.asn.peer.organization.peer.name.value.lower().replace(" ", "_")
            name = f"otto_{org_slug}_{idx}"

            bgp_session = await client.create(
                kind="InfraBGPSession",
                name={"value": name, "owner": account.id, "is_protected": True},
                branch=branch,
                type={"value": "EXTERNAL", "owner": account.id, "is_protected": True},
                status={"value": "active", "owner": account.id, "is_protected": True},
                role={"value": "transit", "owner": account.id, "is_protected": True},
                description={"value": service.description.value, "owner": account.id, "is_protected": True},
                local_as={"id": local_asn.id, "owner": account.id, "is_protected": True},
                peer_group={"id": peer_group.id,"owner": account.id, "is_protected": True}, 
                remote_as={"id": service.asn.peer.id,"owner": account.id, "is_protected": True}, 
                local_ip = {"id": ixp_endpoint.connected_endpoint.peer.ip_addresses.peers[0].id, "owner": account.id, "is_protected": True},
                remote_ip = {"id": ixp_peer.ipaddress.id, "owner": account.id, "is_protected": True},
                device = {"id": ixp_endpoint.connected_endpoint.peer.device.id, "owner": account.id, "is_protected": True},
            )
            await bgp_session.save(allow_upsert=True)
