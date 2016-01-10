from django import template
register = template.Library()

@register.filter(name='get')
def get(mapping, key):
  return mapping.get(key, '')