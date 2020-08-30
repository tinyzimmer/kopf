import re
import ast
import logging


CRD_API_VERSION = 'apiextensions.k8s.io/v1'
CRD_KIND = 'CustomResourceDefinition'
API_VERSION_SCHEMA = {
    'description': 'APIVersion defines the versioned schema of this representation of an object. Servers should convert recognized schemas to the latest internal value, and may reject unrecognized values. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#resources',
    'type': 'string'
}
KIND_SCHEMA = {
    'description': 'Kind is a string value representing the REST resource this object represents. Servers may infer this from the endpoint the client submits requests to. Cannot be updated. In CamelCase. More info: https://git.k8s.io/community/contributors/devel/sig-architecture/api-conventions.md#types-kinds',
    'type': 'string'
}


log = logging.getLogger('crd-util')


class InvalidSpec(Exception):
    pass


def build_cr_from_data(cls, data):
    obj = cls()
    if len(data) == 0:
        return obj
    # Populate the metadata of the object
    if data.get('metadata'):
        log.debug(f'Setting local metadata attributes from {data["metadata"]}')
        obj.name = data['metadata'].get('name') or ""
        obj.namespace = data['metadata'].get('namespace') or ""
        obj.labels = data['metadata'].get('labels') or {}
        obj.annotations = data['metadata'].get('annotations') or {}
        obj.ownerReferences = data['metadata'].get('ownerReferences') or []
    
    if data.get('status'):
        log.debug(f'Setting local status attributes from {data["status"]}')
        obj.status = data['status']

    if data.get('spec'):
        log.debug(f'Setting local spec attributes from {data["spec"]}')
        obj.spec = generate_spec_obj(cls, data.get('spec'))

    return obj    


def generate_crd(crd, cls):
    out = {
        'apiVersion': CRD_API_VERSION,
        'kind': CRD_KIND,
        'metadata': {
            'name': f'{crd.plural}.{crd.group}'
        },
        'spec': {
            'group': crd.group,
            'names': {
                'kind': crd.kind,
                'listKind': crd.listKind,
                'plural': crd.plural,
                'singular': crd.singular
            },
            'scope': crd.scope,
            'versions': [
                {
                    'name': crd.version,
                    'schema': {
                        'openAPIV3Schema': {
                            'description': f'{crd.kind} is the Schema for the {crd.plural} API',
                            'properties': {
                                'apiVersion': API_VERSION_SCHEMA,
                                'kind': KIND_SCHEMA,
                                'metadata': {'type': 'object'},
                                'spec': generate_spec_schema(crd, cls)
                            }
                        }
                    },
                    'served': True,
                    'storage': True
                }
            ]
        }
    }
    if crd.status_subresource:
        out['spec']['versions'][0]['subresources'] = {'status': {}}

    return out
    

def init_val(val):
    if val == str:
        return {'type': 'string'}
    if val == int:
        return {'type': 'integer'}
    if val == bool:
        return {'type': 'boolean'}
    if isinstance(val, tuple):
        out = {'anyOf': []}
        for item in val:
            out['anyOf'].append(init_val(item))
        return out
    if isinstance(val, list):
        if len(val) == 1:
            return {'type': 'array', 'items': init_val(val[0])}
        out = {'type': 'array', 'items': {'anyOf': []}}
        for item in val:
            out['items']['anyOf'].append(init_val(item))
        return out
    if isinstance(val, type):
        return {'type': 'object'}
    if isinstance(val, dict):
        return {'type': 'object'}
    raise Exception(type(val))


def parse_docstr(docstr):
    if not docstr or docstr == '':
        return {}
    fields = re.findall(r'(@[^@]*)', docstr, re.DOTALL)
    out = {}
    for field in fields:
        field = field.strip()
        split = field.split('--')
        name = split[0][1:].strip()
        if len(split) != 2:
            out[name] = ''
        else:
            out[name] = ' '.join(split[1].split())
    return out 


def generate_spec_schema(crd, cls):
    out = {
        'description': f'{crd.kind}Spec defines the desired state of {crd.kind}',
        'properties': {}
    }
    docs = parse_docstr(cls.spec.__doc__)
    specTmpl = cls.spec(cls)
    if not isinstance(specTmpl, dict):
        raise InvalidSpec(f'{specTmpl} is not a valid spec object')
    for key, val in specTmpl.items():
        out['properties'][key] = parse_spec_item(key, val, docs)
    return out


def parse_spec_item(key, val, docs):
    out = init_val(val)

    if docs.get(key) and docs[key] != '':
        out['description'] = docs[key]

    if docs.get(f'{key}.enum'):
        out['enum'] = ast.literal_eval(docs[f'{key}.enum'])

    if out.get('type') == 'array':
        if out['items'].get('type') == 'object':
            out['items']['properties'] = parse_nested_spec_item(val[0])  

    if out.get('type') == 'object':
        out['properties'] = parse_nested_spec_item(val)
    
    return out


def parse_nested_spec_item(cls):
    out = {}

    if callable(getattr(cls, 'attrs', None)):
        attrs = cls.attrs(cls)
        attrDocs = parse_docstr(cls.attrs.__doc__)
        if not isinstance(attrs, dict):
            raise InvalidSpec(f'{attrDocs} is not a valid attributes object')
        for attrName, attrVal in attrs.items():
            out[attrName] = parse_spec_item(attrName, attrVal, attrDocs)

    return out


def generate_spec_obj(cls, data, nested=False):
    class Spec():
        pass

    if nested is False:
        attrTmpl = cls.spec(cls)
        out = Spec()
    else:
        attrTmpl = cls.attrs(cls)
        out = cls()

    for key, valueType in attrTmpl.items():
        attr = data.get(key)
        if not attr:
            setattr(out, key, None)
            continue
        if callable(getattr(valueType, 'attrs', None)):
            setattr(out, key, generate_spec_obj(valueType, attr, nested=True))
            continue
        setattr(out, key, attr)
        
    return out


# def to_markdown(crd):
#     print(crd)
#     crd_spec = crd['spec']
#     crd_names = crd_spec['names']
#     crd_version = crd_spec['versions'][0]
#     # crd_schema = crd_version['schema']['openAPIV3Schema']['properties']['spec']['properties']

#     markdown = ""

#     markdown += f"# {crd_spec['names']['kind']} CRD Reference\n\n"
#     markdown += f"**API Version:** __{crd_spec['group']}/{crd_version['name']}__\n\n"
#     markdown += f"**Scope:** __{crd_spec['scope']}__\n\n"
#     markdown += f"**Singular**: __{crd_names['singular']}__  **Plural:** __{crd_names['plural']}__\n\n"

#     markdown += "\n"

#     markdown += "## Table of Contents\n\n"
#     markdown += f"  * [{crd_spec['names']['kind']}Spec](#{crd_spec['names']['kind']}Spec)\n"
#     # for prop, attrs in crd_schema.items():
#     #     pass

#     return markdown