import cherrypy
import cherrypy.lib.static
import os
import simplejson


import cgi
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter

from semantix.lib import datasources, readers
from semantix.lib.binder.concept.entity import EntityFactory

class HTMLConceptTemlates(object):
    @staticmethod
    def render_article(entity, default_title=None, tags_as_title=False, level=0):
        output = '<div class="section c-article">'

        tags = ''
        if entity.attributes['tags']:
            tags = cgi.escape(entity.attributes['tags'].value)

        title = None
        if entity.attributes['title'] and entity.attributes['title'].value:
            title = entity.attributes['title'].value
        else:
            if default_title:
                title = default_title

        if not title and tags and tags_as_title:
            title = tags

        if title:
            output += '<h%(level)d class="article-title">%(title)s</h%(level)d>' % {
                                                                    'title': cgi.escape(title),
                                                                    'level': level + 1
                                                            }

        content = entity.attributes['content'].value
        if tags == 'code':
            content = highlight(content, get_lexer_by_name('javascript'), HtmlFormatter())
            tags += ' highlight'
        elif tags == 'css':
            content = highlight(content, get_lexer_by_name('css'), HtmlFormatter())
            tags += ' highlight'
        elif tags == 'html':
            content = highlight(content, get_lexer_by_name('html'), HtmlFormatter())
            tags += ' highlight'
        else:
            content = cgi.escape(content)

        if entity.attributes['content']:
            output += '<div class="article-p %s">%s</div>' % (tags, content)

        if entity.links['section']:
            for section in entity.links['section']:
                output += HTMLConceptTemlates.render_article(section, level=level+1, tags_as_title=tags_as_title)

        return output + '</div>'

    @staticmethod
    def render_function(entity):
        def render_function_header(entity):
            output = '<div class="function">'

            if entity.links['return'] is not None:
                output += '<span class="returns">&lt;%s&gt;</span> ' % cgi.escape(entity.links['return'].get(0).attributes['name'].value)

            output += '<span class="name">%s</span><span class="aop">(</span>' % cgi.escape(entity.attributes['name'].value)
            if entity.links['argument'] is not None:
                args = []
                for arg in entity.links['argument']:
                    a = ''

                    if arg.links['type'] is not None:
                        a += '<span class="arg-type">&lt;%s&gt;</span> ' % cgi.escape(arg.links['type'].get(0).attributes['name'].value)

                    a += cgi.escape(arg.attributes['name'].value)

                    args.append(a)

                output += '<span class="dlm">, </span>'.join(args)
            output += '<span class="acp">)</span>'

            if entity.attributes['description']:
                output += '<div class="desc">%s</div>' % cgi.escape(entity.attributes['description'].value)

            return output + '</div>'


        output = '<div class="section c-function">'
        output += render_function_header(entity)

        if entity.links['text']:
            for text in entity.links['text']:
                output += HTMLConceptTemlates.render_article(text, default_title='Description', level=1)

        if entity.links['example']:
            i = 0
            for example in entity.links['example']:
                i += 1
                output += HTMLConceptTemlates.render_article(example, default_title='Example #%s' % i, level=1, tags_as_title=True)

        return output + '</div>'

    @staticmethod
    def default(entity):
        output = '<div class="section default">'

        if entity.attributes['description']:
            output += '<div class="desc">%s</div>' % cgi.escape(entity.attributes['description'].value)

        output += '<dl>'
        attrs_output = ''
        for attr in entity.attributes:
            if attr.name not in ('name', 'description'):
                attrs_output += '<dt>%s</dt><dd>%s</dd>' % (cgi.escape(attr.name), cgi.escape(attr.value))

        if attrs_output:
            output += '<dl>' + attrs_output + '</dl>';

        output += '<h2>Links:</h2>'
        output += '<dl>'
        for link in entity.links:
            output += '<dt>%s</dt>' % cgi.escape(link)

            for el in entity.links[link]:
                output += '<dd><a href="#" id="%s">%s: %s</a>&nbsp;</a></dd>' % (
                                        el.id, cgi.escape(el.concept_name), cgi.escape(el.attributes['name'].value)
                            )
        output += '</dl>'

        return output + '</div>'

    @staticmethod
    def render(entity):
        concept = entity.concept_name
        method = 'render_' + concept.replace('-', '_')

        output = '<div class="topic"><h1>%s' % cgi.escape(entity.concept_name.capitalize())
        if entity.attributes['name']:
            output += ': %s' % cgi.escape(entity.attributes['name'].value)
        output += '</h1>'

        output += getattr(HTMLConceptTemlates, method, HTMLConceptTemlates.default)(entity)

        return output + '</div>'



class Srv(object):
    def __init__(self, config):
        self.current_dir = os.path.dirname(os.path.abspath(__file__))

        config = readers.read(config)
        config['/public'] = {
                                'tools.staticdir.on': True,
                                'tools.staticdir.dir': os.path.join(self.current_dir, 'public')
                            }

        cherrypy.quickstart(self, '/', config=config)

    @cherrypy.expose
    def get(self, id=None):
        ouput = """
        <html>
            <head>
                <meta http-equiv="Content-Type" content="text/html; charset=UTF-8">
                <link rel="stylesheet" type="text/css" href="/public/ext/resources/css/ext-all.css" />
                <link rel="stylesheet" type="text/css" href="/public/resources/highlight.css" />
                <link rel="stylesheet" type="text/css" href="/public/resources/base.css" />
            </head>
            <body>
        """
        entity = EntityFactory.get(int(id))
        return ouput + HTMLConceptTemlates.render(entity) + '</body></html>'

    @cherrypy.expose
    def index(self, *args, **kw):
        return cherrypy.lib.static.serve_file(os.path.join(self.current_dir, 'public', 'index.html'))

    @cherrypy.expose
    def get_tree_level(self, node=None):
        entity_id = node
        if entity_id is not None:
            if entity_id and entity_id != 'root':
                entity_id = int(entity_id)
            else:
                entity_id = None

        return simplejson.dumps(
                                    datasources.fetch('entities.tree.level', entity_id=entity_id)
                                )

    @cherrypy.expose
    def get_topic(self, entity_id):
        if entity_id == 'root':
            return ''

        entity = EntityFactory.get(int(entity_id))
        return HTMLConceptTemlates.render(entity)

Srv('config.yml')
