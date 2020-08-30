import yaml
import logging


from kopf.utilities.crds import (
    build_cr_from_data,
    generate_crd
)


log = logging.getLogger('crd')


class CRD(object):

    def __init__(self,
                 group,
                 version="v1alpha1",
                 singular=None,
                 plural=None,
                 scope="Namespaced",
                 status_subresource=False):
        self.group = group
        self.version = version
        self.singular = singular
        self.plural = plural
        self.scope = scope
        self.status_subresource = status_subresource

    def _set_names(self, cls):
        self.kind = cls.__name__
        self.listKind = f'{self.kind}List'
        if not self.singular:
            self.singular = self.kind.lower()
        if not self.plural:
            self.plural = f'{self.kind.lower()}s'

    def _dict_to_parent(self, cls, data={}):
        log.debug(f'Parsing dict {data} to {cls}')
        return build_cr_from_data(cls, data)

    def _generate_crd_yaml(self, cls, dump=True):
        log.debug(f'Generating CRD yaml for {cls}')
        crd = generate_crd(self, cls)
        if dump is True:
            return yaml.dump(crd, sort_keys=True)
        else:
            return crd

    # # TODO: Not finished yet
    # def _generate_crd_reference(self, cls):
    #     log.debug(f'Generating CRD reference documentation')
    #     return to_markdown(self._generate_crd_yaml(cls, dump=False))

    def __call__(self, parent):

        self._set_names(parent)

        class crd(parent):

            @classmethod
            def generate_k8s(cls):
                return self._generate_crd_yaml(parent)

            @classmethod
            def from_dict(cls, data={}):
                return self._dict_to_parent(parent, data)
            
            @classmethod
            def generate_crd_reference(cls):
                return self._generate_crd_reference(parent)

        return crd

