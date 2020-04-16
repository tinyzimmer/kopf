import urllib.parse
from typing import NamedTuple, Optional, Mapping, List


# TODO: RENAME: ResourceSpec -- to make it less ambiguous which resource we use in different places
# An immutable reference to a custom resource definition.
class Resource(NamedTuple):
    group: str
    version: str
    plural: str

    def __repr__(self):
        return f'{self.name}/{self.version}'

    @property
    def name(self) -> str:
        return f'{self.plural}.{self.group}'.strip('.')

    @property
    def api_version(self) -> str:
        # Strip heading/trailing slashes if group is absent (e.g. for pods).
        return f'{self.group}/{self.version}'.strip('/')

    def get_url(
            self,
            *,
            server: Optional[str] = None,
            namespace: Optional[str] = None,
            name: Optional[str] = None,
            subresource: Optional[str] = None,
            params: Optional[Mapping[str, str]] = None,
    ) -> str:
        if subresource is not None and name is None:
            raise ValueError("Subresources can be used only with specific resources by their name.")

        return self._build_url(server, params, [
            '/api' if self.group == '' and self.version == 'v1' else '/apis',
            self.group,
            self.version,
            'namespaces' if namespace is not None else None,
            namespace,
            self.plural,
            name,
            subresource,
        ])

    def get_version_url(
            self,
            *,
            server: Optional[str] = None,
            params: Optional[Mapping[str, str]] = None,
    ) -> str:
        return self._build_url(server, params, [
            '/api' if self.group == '' and self.version == 'v1' else '/apis',
            self.group,
            self.version,
        ])

    def _build_url(
            self,
            server: Optional[str],
            params: Optional[Mapping[str, str]],
            parts: List[Optional[str]],
    ) -> str:
        query = urllib.parse.urlencode(params, encoding='utf-8') if params else ''
        path = '/'.join([part for part in parts if part])
        url = path + ('?' if query else '') + query
        return url if server is None else server.rstrip('/') + '/' + url.lstrip('/')


# GlobbedResource
# ActualResource
# ResourceRef
# RealResource
# ResourceMask
# ResourceGlob
# ResourceSpec
class ResourceGlob(NamedTuple):
    """
    A pre-parsed glob referencing multiple resources.

    A glob is not usable in API calls, so it has no endpoints/URLs. It is used
    only locally in the operator to match against the actual resources.
    """
    group: str
    version: str
    plural: str

    def check(
            self,
            resource: Resource,
    ) -> bool:
        return (
            (self.group == '*' or self.group == resource.group) and
            (self.version == '*' or self.version == resource.version) and
            (self.plural == '*' or self.plural == resource.plural)
        )
