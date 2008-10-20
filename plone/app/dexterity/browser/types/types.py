import Acquisition
from OFS.interfaces import IItem
from OFS.SimpleItem import Item

from zope.interface import Interface, implements
from zope.component import getAllUtilitiesRegisteredFor, getUtility, getMultiAdapter, ComponentLookupError
from zope.publisher.interfaces.browser import IBrowserPublisher
from zope.app.pagetemplate.viewpagetemplatefile import ViewPageTemplateFile
from zope import schema
from zope.schema.interfaces import IField

from z3c.form import field
from plone.z3cform import layout
from plone.z3cform.crud import crud

from Products.CMFCore.utils import getToolByName
from plone.i18n.normalizer.interfaces import IURLNormalizer

from plone.dexterity.interfaces import IDexterityFTI
from plone.dexterity.fti import DexterityFTI
from plone.app.dexterity.interfaces import ITypesContext
from plone.schemaeditor.browser.schema.schema import SchemaContext


class IAddTypeSettings(Interface):
    """ Define the fields for the content type add form
    """
    
    title = schema.TextLine(
        title = u'Type Name'
        )

    description = schema.Text(
        title = u'Description',
        required = False
        )


class TypeAddForm(crud.AddForm):
    """ Content type add form.  Just a normal CRUD add form with a custom template to show a form title.
    """
    
    label = u'Add Content Type'
    template = ViewPageTemplateFile('../form.pt')


class TypeEditForm(crud.EditForm):
    """ Content type edit form.  Just a normal CRUD form without the form title or edit button.
    """

    label = None
    
    def __init__(self, context, request):
        super(crud.EditForm, self).__init__(context, request)
        self.buttons = self.buttons.copy().omit('edit')


class TypesListing(crud.CrudForm):
    """ The combined content type edit + add forms.
    """
    
    view_schema = field.Fields(IItem).select('title')
    add_schema = IAddTypeSettings
    
    addform_factory = TypeAddForm
    editform_factory = TypeEditForm
    
    def get_items(self):
        """ Look up all Dexterity FTIs via the component registry.
            (These utilities are created via an IObjectCreated handler for the DexterityFTI class,
            configured in plone.dexterity.)
        """
        ftis = getAllUtilitiesRegisteredFor(IDexterityFTI)
        return [(fti.__name__, fti) for fti in ftis]

    def add(self, data):
        """ Add a new DexterityFTI.
            
            A URL normalizer, normally from plone.i18n, is used to sanitize the type's title.
        """
        
        id = getUtility(IURLNormalizer).normalize(data['title'])
        # XXX validation

        fti = DexterityFTI(id)
        fti.id = id
        fti.manage_changeProperties(**data)

        ttool = getToolByName(self.context, 'portal_types')
        ttool._setObject(id, fti)

    def remove(self, (id, item)):
        """ Remove a content type.
        """
        ttool = getToolByName(self.context, 'portal_types')
        ttool.manage_delObjects([id])
        
        # XXX What to do with existing content items?

    def link(self, item, field):
        """ Generate links to the edit page for each type.
            (But only for types with schemata that can be edited through the web.)
        """
        if item.has_dynamic_schema:
            return '%s/%s' % (self.context.absolute_url(), item.__name__)
        else:
            return None

# Create a form wrapper so the form gets layout.
TypesListingPage = layout.wrap_form(TypesListing, label=u'Dexterity content types')


class TypesContext(Item, Acquisition.Implicit):
    """ This class represents the types configlet, and allows us to traverse
        through it to (a wrapper of) the schema of a particular type.
        
        We subclass Item so that this behaves correctly for things like
        absolute_url and the breadcrumbs, and Acquisition.Implicit so that
        we can acquire skin layer items like main_template through this.
    """
    # IBrowserPublisher tells the Zope 2 traverser to pay attention to the
    # publishTraverse and browserDefault methods.
    implements(ITypesContext, IBrowserPublisher)
    
    def __init__(self, context, request):
        super(TypesContext, self).__init__(context, request)
        self.context = context
        self.request = request
        
        # make sure that breadcrumbs will be correct
        self.id = None
        self.Title = lambda: u'Dexterity Content Types'
        
        # turn off green edit border for anything in the type control panel
        request.set('disable_border', 1)
    
    def publishTraverse(self, request, name):
        """ 1. Try to find a content type whose name matches the next URL path element.
            2. Look up its schema.
            3. Return a schema context (an acquisition-aware wrapper of the schema).
        """
        try:
            fti = getUtility(IDexterityFTI, name=name)
        except ComponentLookupError:
            return None
            
        if not fti.has_dynamic_schema:
            # XXX more verbose error?
            raise TypeError, u'This dexterity type cannot be edited through the web.'
        
        schema = fti.lookup_schema()
        return SchemaContext(schema, self.request, name=name, title=fti.title).__of__(self)

    def browserDefault(self, request):
        """ If we aren't traversing to a schema beneath the types configlet, we actually want to
            see the TypesListingPage.
        """
        return self, ('@@edit',)