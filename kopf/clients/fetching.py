import enum
from typing import TypeVar, Optional, Union, Collection, List, Tuple, cast, Iterator

import aiohttp

from kopf.clients import auth
from kopf.clients import discovery
from kopf.structs import bodies
from kopf.structs import resources

_T = TypeVar('_T')

CRD_CRD = resources.Resource('apiextensions.k8s.io', 'v1beta1', 'customresourcedefinitions')


class _UNSET(enum.Enum):
    token = enum.auto()


@auth.reauthenticated_request
async def read_crd(
        *,
        resource: resources.Resource,
        default: Union[_T, _UNSET] = _UNSET.token,
        context: Optional[auth.APIContext] = None,  # injected by the decorator
) -> Union[bodies.RawBody, _T]:
    if context is None:
        raise RuntimeError("API instance is not injected by the decorator.")

    try:
        response = await context.session.get(
            url=CRD_CRD.get_url(server=context.server, name=resource.name),
        )
        response.raise_for_status()
        respdata = await response.json()
        return cast(bodies.RawBody, respdata)

    except aiohttp.ClientResponseError as e:
        if e.status in [403, 404] and not isinstance(default, _UNSET):
            return default
        raise


# TODO: from where this discovery should be invoked? It is unique per client session:
#       different credentials are not only different servers, but also different verbs and permissions.
#       also, we already have caches of resources in APIContext (a session wrapper).
#       => store the results in APIContext
#       => fetch on authetication (when a new ConnectionInfo appears).
@auth.reauthenticated_stream
async def scan_resources(
        *,
        context: Optional[auth.APIContext] = None,  # injected by the decorator
) -> Iterator[resources.Resource]:
    if context is None:
        raise RuntimeError("API instance is not injected by the decorator.")

    server = context.server.rstrip('/')

    # First, scan for /api, specifically for /api/v1 legacy endpoints.
    group_response = await context.session.get(url=f'{server}/api')
    group_response.raise_for_status()
    group_rsp = await group_response.json()
    for version_name in group_rsp['versions']:
        version_response = await context.session.get(url=f'{server}/api/{version_name}')
        version_response.raise_for_status()
        version_rsp = await version_response.json()
        for resource_info in version_rsp['resources']:
            resource_name = resource_info['name']
            yield resources.Resource('', version_name, resource_name)

    # Second, scan for /apis -- newer way of grouping.
    root_response = await context.session.get(url=f'{server}/apis')
    root_response.raise_for_status()
    root_rsp = await root_response.json()
    for group_info in root_rsp['groups']:
        group_name = group_info['name']
        for version_info in group_info['versions']:
            version_name = version_info['version']
            version_response = await context.session.get(url=f'{server}/apis/{group_name}/{version_name}')
            version_response.raise_for_status()
            version_rsp = await version_response.json()
            for resource_info in version_rsp['resources']:
                resource_name = resource_info['name']
                # TODO: Remember other specific names. Some fields are optional:
                # TODO:     resource_info['shortNames'] = ['asfdownloads', 'asfdownload', 'adr']
                # TODO:     resource_info['verbs'] = ['delete', 'deletecollection', 'get', 'list', 'patch', 'create', 'update', 'watch']
                # TODO:     resource_info['singularName'] = 'asfcompetitivedownloadrun'
                # TODO:     resource_info['namespaced'] = True/False
                # TODO:     resource_info['kind'] = 'AsfRun'
                yield resources.Resource(group_name, version_name, resource_name)


@auth.reauthenticated_request
async def read_obj(
        *,
        resource: resources.Resource,
        namespace: Optional[str] = None,
        name: Optional[str] = None,
        default: Union[_T, _UNSET] = _UNSET.token,
        context: Optional[auth.APIContext] = None,  # injected by the decorator
) -> Union[bodies.RawBody, _T]:
    if context is None:
        raise RuntimeError("API instance is not injected by the decorator.")

    is_namespaced = await discovery.is_namespaced(resource=resource, context=context)
    namespace = namespace if is_namespaced else None

    try:
        response = await context.session.get(
            url=resource.get_url(server=context.server, namespace=namespace, name=name),
        )
        response.raise_for_status()
        respdata = await response.json()
        return cast(bodies.RawBody, respdata)

    except aiohttp.ClientResponseError as e:
        if e.status in [403, 404] and not isinstance(default, _UNSET):
            return default
        raise


@auth.reauthenticated_request
async def list_objs_rv(
        *,
        resource: resources.Resource,
        namespace: Optional[str] = None,
        context: Optional[auth.APIContext] = None,  # injected by the decorator
) -> Tuple[Collection[bodies.RawBody], str]:
    """
    List the objects of specific resource type.

    The cluster-scoped call is used in two cases:

    * The resource itself is cluster-scoped, and namespacing makes not sense.
    * The operator serves all namespaces for the namespaced custom resource.

    Otherwise, the namespace-scoped call is used:

    * The resource is namespace-scoped AND operator is namespaced-restricted.
    """
    if context is None:
        raise RuntimeError("API instance is not injected by the decorator.")

    is_namespaced = await discovery.is_namespaced(resource=resource, context=context)
    namespace = namespace if is_namespaced else None

    response = await context.session.get(
        url=resource.get_url(server=context.server, namespace=namespace),
    )
    response.raise_for_status()
    rsp = await response.json()

    items: List[bodies.RawBody] = []
    resource_version = rsp.get('metadata', {}).get('resourceVersion', None)
    for item in rsp['items']:
        if 'kind' in rsp:
            item.setdefault('kind', rsp['kind'][:-4] if rsp['kind'][-4:] == 'List' else rsp['kind'])
        if 'apiVersion' in rsp:
            item.setdefault('apiVersion', rsp['apiVersion'])
        items.append(item)

    return items, resource_version
