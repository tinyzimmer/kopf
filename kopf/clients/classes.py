from typing import Type

import pykube

from kopf.clients import auth
from kopf.structs import resources


def make_cls(
        resource: resources.Resource,
) -> Type[pykube.objects.APIObject]:

    api = auth.get_pykube_api()
    all_resources = api.resource_list(resource.api_version)['resources']
    this_resource = [r for r in all_resources if r['name'] == resource.plural]
    if not this_resource:
        raise pykube.ObjectDoesNotExist(f"No such CRD: {resource.name}")

    resource_kind = this_resource[0]['kind']
    is_namespaced = this_resource[0]['namespaced']

    cls_name = resource.plural
    cls_base = pykube.objects.NamespacedAPIObject if is_namespaced else pykube.objects.APIObject
    cls = type(cls_name, (cls_base,), {
        'version': resource.api_version,
        'endpoint': resource.plural,
        'kind': resource_kind,
    })
    return cls
