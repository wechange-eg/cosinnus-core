from django import template
from django.template.loader import render_to_string
from menus.templatetags.menu_tags import PageLanguageUrl
from classytags.arguments import Argument
from classytags.core import Options

register = template.Library()


def do_show_sibling_menu(parser, token):
    try:
        # split_contents() knows not to split quoted strings.
        tag_name, node, template_path = token.split_contents()
    except ValueError:
        raise template.TemplateSyntaxError("%r tag requires a single argument" % token.contents.split()[0])
    if not (template_path[0] == template_path[-1] and template_path[0] in ('"', "'")):
        raise template.TemplateSyntaxError("%r tag's argument should be in quotes" % tag_name)
    return SiblingMenuNode(node, template_path[1:-1])


class SiblingMenuNode(template.Node):
    def __init__(self, node, template_path):
        self.node = template.Variable(node)
        self.template_path = template_path

    def render(self, context):
        try:
            actual_node = self.node.resolve(context)
            # Level 2/3: show children
            if actual_node.level in (2, 3):
                nodes = actual_node.children.filter(in_navigation=True).all()
            # Else: show siblings
            else:
                nodes = actual_node.parent.children.filter(in_navigation=True).all()
            if len(nodes) > 0:
                return render_to_string(self.template_path, {'nodes': nodes, 'current_page': context['current_page']})
        except:
            pass
        return ''


register.tag('show_sibling_menu', do_show_sibling_menu)


@register.filter
def subtract(value, arg):
    return value - arg

