from typing import Union

from infrahub_sdk import InfrahubClient, InfrahubNode
from infrahub_sdk.exceptions import NodeNotFoundError
from infrahub_sdk.generator import InfrahubGenerator
from infrahub_sdk.node import RelatedNode, Attribute

# from utils import inherit_attribute_from_hierarchy, InheritanceException

async def inherit_attribute_from_hierarchy(
    client: InfrahubClient, node: InfrahubNode, attribute: str
) -> Union[int, str, bool, InfrahubNode]:
    if hasattr(node, attribute):
        attr = getattr(node, attribute)
        if isinstance(attr, RelatedNode) and attr.schema.cardinality == "one":
            await attr.fetch()
            return attr.peer
        elif isinstance(attr, RelatedNode) and attr.schema.cardinality == "many":
            raise InheritanceException(f"Relationships of cardinality many are not supported!")
        elif isinstance(attr, Attribute):
            return attr.value

    if not hasattr(node, "parent"):
        raise InheritanceException(f"Could not resolve {attribute} for {node.typename}")

    await node.parent.fetch()

    if not node.parent.peer:
        raise InheritanceException(f"Could not resolve {attribute} for {node.typename}")

    return await inherit_attribute_from_hierarchy(client, node.parent.peer, attribute)


class InheritanceException(Exception):
    pass


class Generator(InfrahubGenerator):
    async def generate(self, data: dict) -> None:
        ixp = await self.client.get("InfraIXP", id=data["InfraIXPBGPPrivatePeering"]["edges"][0]["node"]["ixp"]["node"]["id"], include=["sites"])
        asn = await self.client.get("InfraAutonomousSystem", id=data["InfraIXPBGPPrivatePeering"]["edges"][0]["node"]["asn"]["node"]["id"])
        await asn.organization.fetch()
        org = asn.organization.peer

        await ixp.sites.fetch()
        sites = ixp.sites.peers

        ixp_peers = await self.client.filters("InfraIXPPeer", ixp__ids=[ixp.id], asn__ids=[asn.id])

        ixp_endpoints = await self.client.filters(
            kind="InfraIXPEndpoint",
            ixp__ids=[ixp.id]
        )

        if len(ixp_peers) != len(ixp_endpoints) and ixp.redundant.value:
            raise ValueError("Redundancy is required but the amount of IXP Peers does not match the amount the amount of endpoints")

        if not data["InfraIXPBGPPrivatePeering"]["edges"][0]["node"]["redundant"]["value"]:
            ixp_peers = [ixp_peers[0]]
            ixp_endpoints = [ixp_endpoints[0]]

        local_asn = await self.client.get(
            "InfraAutonomousSystem", asn__value=64496
        )

        try:
            account = await self.client.get("CoreAccount", name__value="Generator")
        except NodeNotFoundError:
            raise ValueError("Unable to find CoreAccount Generator in Infrahub")

        try:
            peer_group = await inherit_attribute_from_hierarchy(
                self.client, sites[0].peer, "bgp_peer_group"
            )
        except InheritanceException:
            peer_group = None

        for idx, (ixp_peer, ixp_endpoint) in enumerate(zip(ixp_peers, ixp_endpoints), start=1):

            await ixp_peer.ipaddress.fetch()

            await ixp_endpoint.connected_endpoint.fetch()
            await ixp_endpoint.connected_endpoint.peer.ip_addresses.fetch()
            await ixp_endpoint.connected_endpoint.peer.device.fetch()

            org_slug = org.name.value.lower().replace(" ", "_")
            ixp_slug = ixp.name.value.lower().replace(" ", "_")
            name = f"{org_slug}_{ixp_slug}_{idx}"


            bgp_session = await self.client.create(
                kind="InfraBGPSession",
                name={"value": name, "owner": account.id, "is_protected": True},
                type={"value": "EXTERNAL", "owner": account.id, "is_protected": True},
                status={"value": "active", "owner": account.id, "is_protected": True},
                role={"value": "peering", "owner": account.id, "is_protected": True},
                local_as={"id": local_asn.id, "owner": account.id, "is_protected": True},
                peer_group={"id": peer_group.id,"owner": account.id, "is_protected": True}, 
                remote_as={"id": asn.id,"owner": account.id, "is_protected": True}, 
                local_ip = {"id": ixp_endpoint.connected_endpoint.peer.ip_addresses.peers[0].id, "owner": account.id, "is_protected": True},
                remote_ip = {"id": ixp_peer.ipaddress.id, "owner": account.id, "is_protected": True},
                device = {"id": ixp_endpoint.connected_endpoint.peer.device.id, "owner": account.id, "is_protected": True},
            )
            await bgp_session.save(allow_upsert=True)
