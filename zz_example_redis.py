import kopf

@kopf.CRD(group="kopf.io")
class ZZRedisCluster(object):

    def namespaced_name(self):
        return f'{self.namespace}/{self.name}'

    def spec(self):
        """
        @config -- Configuration options for redis pointing to custom class.
                   You can use multiline strings.

        @someString -- This is an example string. It also specifies an enum. 
        @someString.enum -- ['option-a', 'option-b']

        @someBool -- This is an example boolean.

        @someInt -- This is an example integer.

        @someList -- This is an example array of strings.

        @someDynamicList -- This is an example of an array that can contain strings and integers.
        
        @someDynamicItem -- This is an example of a single field that can be a string or integer.
        """
        return {
            'config': RedisConfig,
            'someString': str,
            'someBool': bool,
            'someInt': int,
            'someList': [str],
            'someDynamicList': [str, int],
            'someDynamicItem': (str, int)
        }

class RedisConfig(object):

    def attrs(self):
        """
        @someString -- This is an example string inside the redis config.
        """
        return {
            'someString': str
        }
