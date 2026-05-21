from django import template

register = template.Library()


@register.filter('klass')
def klass(ob):
    return ob.__class__.__name__


@register.filter('startswith')
def startswith(value, arg):
    return value.startswith(arg)
