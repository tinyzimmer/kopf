import kopf
import pykube
import yaml


@kopf.on.create('zalando.org', 'v1', 'kopfexamples')
def kex_created(spec, name, **kwargs):
    doc = yaml.safe_load(f"""
        apiVersion: batch/v1
        kind: Job
        spec:
          backoffLimit: 0
          template:
            spec:
              restartPolicy: Never
              containers:
              - name: the-only-one
                image: busybox
                command: ["sh", "-x", "-c"]
                args: 
                - |
                  env|sort
                  sleep {spec.get('duration', 0)}
                env:
                - name: FIELD
                  value: {spec.get('field', 'default-value')}
    """)
    kopf.adopt(doc)
    kopf.label(doc, {'parent-name': name}, nested=['spec.template'])

    child = pykube.Job(api, doc)
    child.create()


@kopf.on.event('', 'v1', 'pods', labels={'parent-name': None})
def event_in_a_pod(meta, status, namespace, **kwargs):
    phase = status.get('phase')  # make a decision!
    query = KopfExample.objects(api, namespace=namespace)
    parent = query.get_by_name(meta['labels']['parent-name'])
    parent.patch({'status': {'children': phase}})


class KopfExample(pykube.objects.NamespacedAPIObject):
    version = "zalando.org/v1"
    endpoint = "kopfexamples"
    kind = "KopfExample"


api = pykube.HTTPClient(pykube.KubeConfig.from_env())
