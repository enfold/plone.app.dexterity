from Products.Five.browser.metaconfigure import ViewMixinForTemplates
from zope.browserpage.viewpagetemplatefile import ViewPageTemplateFile
from Products.Five import BrowserView


# The widget rendering templates need to be Zope 3 templates
class RenderWidgets(ViewMixinForTemplates, BrowserView):
    index = ViewPageTemplateFile('render_widgets.pt')
