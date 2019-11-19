import kopf


@kopf.on.login()
def remote_cluster_a(**kwargs):
    return kopf.ConnectionInfo(
        server='https://remote-kubernetes/',
        token='abcdef123')


@kopf.on.create('zalando.org', 'v1', 'kopfexamples')
def kex_created(name, **kwargs):
    print(name)


