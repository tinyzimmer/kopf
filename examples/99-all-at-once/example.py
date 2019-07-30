"""
Kubernetes operator example: all the features at once (for debugging & testing).
"""
import pprint
import time

import kopf
import pykube
import yaml

# Marks for the e2e tests (see tests/e2e/test_examples.py):
E2E_CREATE_TIME = 5
E2E_DELETE_TIME = 1
E2E_TRACEBACKS = True

try:
    cfg = pykube.KubeConfig.from_service_account()
except FileNotFoundError:
    cfg = pykube.KubeConfig.from_file()
api = pykube.HTTPClient(cfg)


@kopf.on.create('zalando.org', 'v1', 'kopfexamples')
def create_1(body, meta, spec, status, **kwargs):
    children = _create_children(owner=body)

    kopf.info(body, reason='AnyReason')
    kopf.event(body, type='Warning', reason='SomeReason', message="Cannot do something")
    kopf.event(children, type='Normal', reason='SomeReason', message="Created as part of the job1step")

    return {'job1-status': 100}


@kopf.on.create('zalando.org', 'v1', 'kopfexamples')
def create_2(body, meta, spec, status, retry=None, **kwargs):
    wait_for_something()  # specific for job2, e.g. an external API poller

    if not retry:
        # will be retried by the framework, even if it has been restarted
        raise Exception("Whoops!")

    return {'job2-status': 100}


@kopf.on.update('zalando.org', 'v1', 'kopfexamples')
def update(body, meta, spec, status, old, new, diff, **kwargs):
    print('Handling the diff')
    pprint.pprint(list(diff))


@kopf.on.field('zalando.org', 'v1', 'kopfexamples', field='spec.lst')
def update_lst(body, meta, spec, status, old, new, **kwargs):
    print(f'Handling the FIELD = {old} -> {new}')


@kopf.on.delete('zalando.org', 'v1', 'kopfexamples')
def delete(body, meta, spec, status, **kwargs):
    pass


def _create_children(owner):
    return []


def wait_for_something():
    # Note: intentionally blocking from the asyncio point of view.
    time.sleep(1)


@kopf.on.create('zalando.org', 'v1', 'kopfexamples')
def create_pod(body, **kwargs):

    # Render the pod yaml with some spec fields used in the template.
    pod_data = yaml.safe_load(f"""
        apiVersion: v1
        kind: Pod
        spec:
          containers:
          - name: the-only-one
            image: busybox
            command: ["sh", "-x", "-c", "sleep 1"]
    """)

    # Make it our child: assign the namespace, name, labels, owner references, etc.
    kopf.adopt(pod_data, owner=body)
    kopf.label(pod_data, {'application': 'kopf-example-10'})

    # Actually create an object by requesting the Kubernetes API.
    pod = pykube.Pod(api, pod_data)
    pod.create()


@kopf.on.event('', 'v1', 'pods', labels={'application': 'kopf-example-10'})
def example_pod_change(logger, **kwargs):
    logger.info("This pod is special for us.")

####################################################################################################
# Ideas on how to declare resource relations:

# (+) conventient and short
# (-) easy to miss the context switch when reading.
# (-) multi-decorator approach needs state storing, conflict resolution.
# (+) there can be many relations, all under different names. e.g. 2 parents, 1 selector. Some with many items?
@kopf.on.create('', 'v1', 'pods')
@kopf.on.update('', 'v1', 'pods')
@kopf.on.delete('', 'v1', 'pods')
@kopf.relation('zalando.org', 'v1', 'kopfexamples', name='parent')
def example_pod_change(logger, parent, **kwargs):
    pass


@kopf.on.event('', 'v1', 'pods')
@kopf.on.create('', 'v1', 'pods')
@kopf.on.update('', 'v1', 'pods')
@kopf.on.delete('', 'v1', 'pods')
@kopf.go.owner('zalando.org', 'v1', 'kopfexamples', alias='parent')
@kopf.use.owner('zalando.org', 'v1', 'kopfexamples', alias='parent')
def example_pod_change(logger, parent, **kwargs):
    pass


# owned = kopf.via.selector('zalando.org', 'v1', 'kopfexamples')
owned = kopf.via.owner('zalando.org', 'v1', 'kopfexamples')
@owned.on.create('', 'v1', 'pods')
@owned.on.update('', 'v1', 'pods')
@owned.on.delete('', 'v1', 'pods')
@owned.on.event('', 'v1', 'pods')
def when_pod_changed(logger, parent, **kwargs):
    pass  # !!! it must be kopfexamples here! but events of a child pod.


# This would be the most nice looking, but causes a syntax error.
# (!) syntactically impossible.
# (-) not obvious, that the kwargs will be for owner.
# (-) looks like regular filtering, not context switching.
@kopf.on.create('', 'v1', 'pods').of.owner('zalando.org', 'v1', 'kopfexamples')
@kopf.on.update('', 'v1', 'pods').of.owner('zalando.org', 'v1', 'kopfexamples')
@kopf.on.delete('', 'v1', 'pods').of.owner('zalando.org', 'v1', 'kopfexamples')
@kopf.on.event('', 'v1', 'pods').of.owner('zalando.org', 'v1', 'kopfexamples')
def when_pod_changed(logger, parent, **kwargs):
    pass  # !!! it must be kopfexamples here! but events of a child pod.


@kopf.on.create('', 'v1', 'pods')
@kopf.on.update('', 'v1', 'pods')
@kopf.on.delete('', 'v1', 'pods')
@kopf.on.event('', 'v1', 'pods')
@kopf.focus.on.owner('zalando.org', 'v1', 'kopfexamples')
def when_pod_changed(logger, parent, **kwargs):
    pass  # !!! it must be kopfexamples here! but events of a child pod.


@kopf.on.related.create('', 'v1', 'pods', 'zalando.org', 'v1', 'kopfexamples')
@kopf.on.related.update('', 'v1', 'pods', 'zalando.org', 'v1', 'kopfexamples')
@kopf.on.related.delete('', 'v1', 'pods', 'zalando.org', 'v1', 'kopfexamples')
@kopf.on.related.event('', 'v1', 'pods', 'zalando.org', 'v1', 'kopfexamples')
def when_pod_changed(logger, parent, **kwargs):
    pass  # !!! it must be kopfexamples here! but events of a child pod.


# THIS ONE looks the most promising:
# (+) same event system, just subject and context split (default: the same).
# (+) watched resource is clearly mentioned.
# (+) can be styled both subject-context and context-subject for readability.
# (-) not so obvious that the kwargs are of context resource, though tolerable.
# (-) `via` is explicitly needed in this case, in addition to `context`.
# (-) An implicit API GET is needed to fetch the data of the related resource.
# (-) An implicit API GET is needed to fetch the list of the related resources, filtered(how?).
# (?) HOW to behave when 1 event comes on a subject with N contexts (e.g. reversed way: parent->child). Call for each?
@kopf.on.create(subject=('', 'v1', 'pods'), context=('zalando.org', 'v1', 'kopfexamples'), via=kopf.OWNERSHIP)
@kopf.on.update(subject=('', 'v1', 'pods'), context=('zalando.org', 'v1', 'kopfexamples'), via=kopf.OWNERSHIP)
@kopf.on.delete(subject=('', 'v1', 'pods'), context=('zalando.org', 'v1', 'kopfexamples'), via=kopf.OWNERSHIP)
@kopf.on.event(subject=('', 'v1', 'pods'), context=('zalando.org', 'v1', 'kopfexamples'), via=kopf.OWNERSHIP)
def when_pod_changed(logger, parent, **kwargs):
    pass  # !!! it must be kopfexamples here! but events of a child pod.


# Same as before, but a bit shorter.
@kopf.on.create(subject=('', 'v1', 'pods'), context=kopf.owner('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.update(subject=('', 'v1', 'pods'), context=kopf.owner('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.delete(subject=('', 'v1', 'pods'), context=kopf.owner('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.event(subject=('', 'v1', 'pods'), context=kopf.owner('zalando.org', 'v1', 'kopfexamples'))
def when_pod_changed(logger, parent, **kwargs):
    pass  # !!! it must be kopfexamples here! but events of a child pod.


@kopf.on.create.owned(subject=('', 'v1', 'pods'), context=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.update.owned(subject=('', 'v1', 'pods'), context=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.delete.owned(subject=('', 'v1', 'pods'), context=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.event.owned(subject=('', 'v1', 'pods'), context=('zalando.org', 'v1', 'kopfexamples'))
def when_pod_changed(logger, parent, **kwargs):
    pass  # !!! it must be kopfexamples here! but events of a child pod.


####################################################################################################
# ALTERNATIVE APPROACH:
# Do not watch on resources, watch on their relations directly!
# (-) Nah! That looks stupid.

@kopf.on.create(kopf.relation(owned=('', 'v1', 'pods'), owner=('zalando.org', 'v1', 'kopfexamples')))
@kopf.on.update(kopf.relation(owned=('', 'v1', 'pods'), owner=('zalando.org', 'v1', 'kopfexamples')))
@kopf.on.delete(kopf.relation(owned=('', 'v1', 'pods'), owner=('zalando.org', 'v1', 'kopfexamples')))
@kopf.on.event(kopf.relation(owned=('', 'v1', 'pods'), owner=('zalando.org', 'v1', 'kopfexamples')))
def when_pod_changed(logger, parent, **kwargs):
    pass  # !!! it must be kopfexamples here! but events of a child pod.


# (-) Efficiently, the same as the subject/context thing for per-object decorators.
@kopf.on.create(kopf.relation(source=('', 'v1', 'pods'), target=('zalando.org', 'v1', 'kopfexamples'), via=kopf.OWNERSHIP))
@kopf.on.update(kopf.relation(source=('', 'v1', 'pods'), target=('zalando.org', 'v1', 'kopfexamples'), via=kopf.OWNERSHIP))
@kopf.on.delete(kopf.relation(source=('', 'v1', 'pods'), target=('zalando.org', 'v1', 'kopfexamples'), via=kopf.OWNERSHIP))
@kopf.on.event(kopf.relation(source=('', 'v1', 'pods'), target=('zalando.org', 'v1', 'kopfexamples'), via=kopf.OWNERSHIP))
def when_pod_changed(logger, parent, **kwargs):
    pass  # !!! it must be kopfexamples here! but events of a child pod.


@kopf.on.create(kopf.resource('', 'v1', 'pods').owner('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.update(kopf.resource('', 'v1', 'pods').owner('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.delete(kopf.resource('', 'v1', 'pods').owner('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.event(kopf.resource('', 'v1', 'pods').owner('zalando.org', 'v1', 'kopfexamples'))
def when_pod_changed(logger, parent, **kwargs):
    pass  # !!! it must be kopfexamples here! but events of a child pod.


####################################################################################################
# ALTERNATIVE APPROACH:
# Do not modify the event system at all.
# Instead, provide the context selectors for specific operations only.
#
# (?) HOW to pass all kwargs of the related object?
# (-) Looks like a job of a client lib, except for the current object context.
# (+) Similar to kopf.label() & kopf.adopt() when current object is implicit.
# (+) No implicit API reads, only explicit API reads; watch-event data are for the altered object only.
# (+) Uses the client library of user's choice.
# (-) Need to explicitly filter pods which are owned by / related to these parents, to avoid dummy handling.
# (-) Cannot filter by extra criteria on the related resources (e.g. parent's labels).
@kopf.on.event('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.create('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.update('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.delete('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
def example_pod_change(logger, **kwargs):

    for kex in KopfExample.objects(api).get(...???...):  # TODO: and what is here?
        kex.patch({'status': {'xyz': 100}})

    for owner in kopf.owners('zalando.org', 'v1', 'kopfexamples'):
        kex = KopfExample(api, owner)
        kex.patch({'status': {'xyz': 100}})

    with kopf.owners('zalando.org', 'v1', 'kopfexamples') as owners:  # why at all?
        for owner in owners:
            kex = KopfExample(api, owner)
            kex.patch({'status': {'xyz': 100}})

    for pod in kopf.selector('', 'v1', 'pods', field='spec.selector'):  # is it our concern?
        pod = pykube.Pod(api, pod)
        pod.patch({'status': {'xyz': 100}})


####################################################################################################
# ==> The whole idea of switching the context is conceptually wrong here.
# This should be done by a client library. Kopf is not a client library.
#
# The original use-case was:
# > When one of my children pods changes, I want to decide something on the parent resource.
#
# This is also wrong: the decision is usually made on all pods of that parent, not only one.
# Without the cross-object communication feature, a fake field is needed:
# to be modified in children, to trigger the parent events, just implicitly.
#
# To implement this feature, one of these options will be needed anyway:
# * Either an implicit GET with selectors/filters/names/uids before going to the handler.
# * Or an internal state on the related resource, for triggering the change there.
#
# However, in some cases, the state change might be intentionally skipped: e.g. for dummy pod changes.
# This can be defined on the handlers level and domain logic, but not implicitly in the framework.
# The framework will transfer **all** changes, even when it is not needed at all.
#
# This, however, can be implemented as a storage of ALL children minified states (same as last-seen)
# on the parent's/related object's status field.
@kopf.on.event('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.create('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.update('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.delete('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.to.field('zalando.org', 'v1', 'kopfexamples', field='status.children-pods', via=kopf.OWNERSHIP)
def fn(**_):
    pass   # TODO: and what is here?
#
# Or, the "to"-redirector can just forward the result only.
# The default is "to" the current object, as it is. It changes the behaviour ONLY when added.
@kopf.on.event('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.create('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.update('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.delete('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.to.field('zalando.org', 'v1', 'kopfexamples', field='status.children-pods', via=kopf.OWNERSHIP)
def fn(status, **_):
    return status
#
# Or, we can specify alternative and multiple targets for the result.
@kopf.on.event('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.create('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.update('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.delete('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.to.owners('zalando.org', 'v1', 'kopfexamples', field='status.children-pods')  # via owner-references, no extra params
@kopf.to.labels('zalando.org', 'v1', 'kopfexamples', field='status.children-pods', labels={})  # to all objects matching the labels
@kopf.to.selectors('zalando.org', 'v1', 'kopfexamples', field='status.children-pods', selector='spec.selector')  # where current pod matches the selector
@kopf.to.related('zalando.org', 'v1', 'kopfexamples', field='status.children-pods', fn=lambda **_: False)  # arbitrary selector callback
def child_pod_handler(status, **_):
    if status.get('phase') == 'Completed':
        return status
#
# And the related resources handle it themselves. Maybe even in other sibling operators.
@kopf.on.field('zalando.org', 'v1', 'kopfexamples', field='status.children-pods')
def kex_children_pods_changed(new, **_):
    for pod_key, pod_val in new.items():
        pass  # make a decision -- cumulatively on all pods
#
# (+) Full control over the event/cause types of the monitored objects. Event per-field.
# (?) Can be solved without GET requests (probably), just by assuming the namespaces/names.
# (-) GETs are needed for labels/selectors/fn checking.
# (-) Explicit filtering is needed for owners, or maybe by labels.
# (?) Filters can be implicitly injected by the to-decorators -- of there is nothing expected to be done.
#
####################################################################################################
# IDEA:
# It can be possible to use the handler functions themselves for relations.
# All necessary fields/filters will be guessed from the decorators of that function.
# Read as: "call the handler when triggered by fn() in context of an affected KopfExample".
# Technically: when triggered by one of the changes defined in fn()'s @kopf.to-decorators.
# In this example, all of owners/labels/selectors/callbacks can be taken into account.
# In that case, target field is not needed to be specified, it can be auto-named and auto-guessed.
@kopf.on.event('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.create('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.update('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.on.delete('', 'v1', 'pods', owner=('zalando.org', 'v1', 'kopfexamples'))
@kopf.to.owners()  # all onwers, regardless of kind (they are known in advance, not need for GETs)
@kopf.to.owners('zalando.org', 'v1', 'kopfexamples')  # via owner-references, no extra params
@kopf.to.related('zalando.org', 'v1', 'kopfexamples', fn=lambda **_: False)  # arbitrary selector callback
@kopf.to.labeled('zalando.org', 'v1', 'kopfexamples', labels={})  # to all objects matching the labels
@kopf.to.selecting('zalando.org', 'v1', 'kopfexamples', selector='spec.selector')  # where current pod matches the selector
def child_pod_handler(status, **_):
    if status.get('phase') == 'Completed':
        return status
#
@kopf.on.field('zalando.org', 'v1', 'kopfexamples', source=child_pod_handler)  # on.field()? or on.result()? it can be many fields.
def kex_children_pods_changed(new, **_):
    for pod_key, pod_status in new.items():
        pass  # make a decision -- cumulatively on all pods
#
####################################################################################################
# IDEA:
# The concept of "origin" or "source" can also be used for creation handlers, if triggered via `kopf.adopt()`.
# Basically, a replacement for labelling, just implicit, with function references.
# However, it is a mixed usage of origins of the object being handled, and origins of the changes: to be clarified.
# TODO: Terminology:
# TODO: "origin" is a resource(+handler) that produced the handled resource, according to the records from kopf.originate().
# TODO: "??????" is a handler function that was the source of the result delivered as a status field update.
# TODO: keep in mind: it can be a string, if it is a cross-app communication.
@kopf.on.create('zalando.org', 'v1', 'kopfexamples')
def create_kex(**_):
    obj = {}
    # kopf.originate(obj, annotation='zalando.org/origin')  # <-- sets the data for origin detection
    # kopf.originate(obj, label='zalando.org/origin')  # <-- sets the data for origin detection
    # kopf.originate(obj, field='status.my-origin')  # <-- sets the data for origin detection
    kopf.originate(obj)  # <-- sets the data for origin detection
    kopf.adopt(obj)  # <-- sets the data for origin detection
    pod = pykube.Pod(api, obj).create()
#
@kopf.on.create('', 'v1', 'pods', origin=('zalando.org', 'v1', 'kopfexamples'))  # by resource only, any handler
@kopf.on.create('', 'v1', 'pods', origin=create_kex)                             # by handler (resources are assumed)
@kopf.on.update('', 'v1', 'pods', origin=create_kex)  # FIXME: this origin does not cause updates. RESOLVED? now, it is just a resource.
@kopf.on.delete('', 'v1', 'pods', origin=create_kex)  # FIXME: this origin does not cause deletions. RESOLVED? now, it is just a resource.
@kopf.to.owners(keys=['metadata.namespace', 'metadata.name']) # <-- to all owners (can be arbitrary controllers).
@kopf.to.origin(key='metadata.uid')  # <-- to the specific object that created this pod. Not just the owner/owners (can be arbitrarily).
def pod_handler_if_created_via_kex_creation(status, **_):
    if status.get('phase') == 'Completed':
        return status
#
# TODO: naming:
# TODO: not "on.result of kopfexamples" (misleading), but some other word for another handler's result delivery.
# TODO: maybe on.data()? on.handler()? on.result()? on.origin() [but terminology conflicts]?
# @kopf.on.relation('zalando.org', 'v1', 'kopfexamples', handler=pod_handler_if_created_via_kex_creation)
# @kopf.on.handler('zalando.org', 'v1', 'kopfexamples', handler=pod_handler_if_created_via_kex_creation)
# @kopf.on.result('zalando.org', 'v1', 'kopfexamples', source=pod_handler_if_created_via_kex_creation)  # TODO: naming?
@kopf.on.update('zalando.org', 'v1', 'kopfexamples', source=pod_handler_if_created_via_kex_creation)  # TODO: but how do we know? if it is not a specific field. Only if that field has changed?
@kopf.on.status('zalando.org', 'v1', 'kopfexamples', source=pod_handler_if_created_via_kex_creation)  # TODO: Good! Aligned with on.field, on.condition, on.scale (later), on.{subresource/action}.
@kopf.on.field('zalando.org', 'v1', 'kopfexamples', source=pod_handler_if_created_via_kex_creation)   # TODO: Good! Aligned with on.condition, on.scale (later), on.{subresource/action}.
def kex_has_its_pods_updated(new, **_):
    for pod_key, pod_status in new.items():
        pass  # make a decision -- cumulatively on all pods
#
# This, eventually, can lead to one-handler constructs as in the initial attempt:
# i.e. with some assumed default fields for data exchange, and clear understanding
# what context is used. The related objects are not delivered at all directly,
# but rather their full bodies (or only statuses?), via in-object representation.
# Arbitrary selections are possible, as they effectively will be passed to
# implicit @on.event(...) on the related resource with an empty function.
# ==> I.e., automatic expansion of a two-liner to the abovementioned patterns:
@kopf.on.relation(of=kopf.Resource('zalando.org', 'v1', 'kopfexamples'),
                  to=kopf.Resource('', 'v1', 'pods', labels={}, filter=..., origin=create_kex))
def kex_has_its_pods_updated(target, targets, **_):
    for pod_key, pod_status in targets.items():
        pass  # make a decision -- cumulatively on all pods
#
# DRAFTING:
#   The question is: how intuitive or misleading is it? How pythonic is it?
#   Try in our code of our apps with this approach (as if it is already implemented):
#       does it look better? shorter? fewer if's? fewer fields?
#   The same for ephemeral-storage-claims?
#
####################################################################################################
# ROADMAP:
# * contextual info:
#   * current resource & object & handler via contextvars.
#   * usage in adopt() & co, with optional owner=...
#   * docs
# * "@kopf.to" result redirection:
#   * decorators
#   * result storing to self
#   * result storing to owners
#   * field specifiers
#   * field auto-guessing
#   * key/keys structuring, or flat merges
#   * docs
# * origination and filtering by origins -- mimic Job auto-labelling:
#   * kopf.originate() + adopt()
#   * kopf.to.origin() decorator
#   * origin=... filter by function reference
#   * origin=... filter by string handler id
#   * docs
# * @kopf.on.status: -- IS IT NEEEDED AT ALL? What are the benefits, if on.update/on.field do exist?
#   * decorator
#   * handling (same as on.field, with the status keys handled by Kopf).
#   * docs
# * "@kopf.on" by result redirection from "@kopf.to":
#   * new decorators, if any (see also @kopf.on.status nearby)
#   * source=... field guessing (or storing & getting on the function?).
#   * on.update filters for specific field changed (but in the context of the whole object).
#   * docs
# * extra "@kopf.to" targets:
#   * related, labeled, selecting, etc (is it needed in the first stage?)
#   * docs
####################################################################################################
