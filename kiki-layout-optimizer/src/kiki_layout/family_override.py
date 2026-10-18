"""Strict UUID-based manual family merge/split overrides.

The UI may consolidate or separate user-reviewed silhouette groups without
modifying Illustrator artwork. A complete UUID partition avoids accidental
unmapped objects and silently changing other families after a re-export.
"""
from __future__ import annotations

import re


def apply_family_overrides(data, override):
    if not isinstance(override, dict) or override.get("schema") != 1:
        raise ValueError("Manual family groups require schema=1")
    if override.get("document_name") != data.get("document_name"):
        raise ValueError("Manual family groups belong to a different document")
    groups=override.get("groups")
    if not isinstance(groups,list) or not groups or len(groups)>1000:
        raise ValueError("Manual family groups must contain 1–1000 groups")
    objects=data.get("objects",[])
    uuid_to_id={}
    for ob in objects:
        uid=str(ob.get("uuid",""))
        if not uid or uid in uuid_to_id:
            raise ValueError("Manual family groups require unique Illustrator UUIDs")
        uuid_to_id[uid]=str(ob["id"])
    found={}
    used_group_ids=set()
    for index,group in enumerate(groups):
        if not isinstance(group,dict):
            raise ValueError("Manual group must be an object")
        name=group.get("id",str(index))
        if not isinstance(name,str) or not re.fullmatch(r"[\w.-]{1,128}",name):
            raise ValueError("Unsafe manual family group identifier")
        if name in used_group_ids:
            raise ValueError("Duplicate manual family group identifier")
        used_group_ids.add(name)
        members=group.get("uuids")
        if not isinstance(members,list) or not members or len(members)>1000:
            raise ValueError("Manual group must contain valid UUIDs")
        for uid in members:
            if not isinstance(uid,str) or uid not in uuid_to_id:
                raise ValueError("Manual family UUID missing from current Illustrator export; review grouping")
            if uid in found:
                raise ValueError("Manual family UUID belongs to multiple groups")
            found[uid]="user:"+name
    if set(found)!=set(uuid_to_id):
        raise ValueError("Manual family groups do not cover the current selected artwork")
    return {oid:found[uid] for uid,oid in uuid_to_id.items()}
