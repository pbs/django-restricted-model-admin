from django.test import TestCase
from django.contrib.sites.models import Site
from django.contrib.auth.models import User, Group
from django.contrib.admin.options import ModelAdmin
from django.conf import settings
from cms.models.permissionmodels import GlobalPagePermission
from test_model import TestModel
from decorators import \
    (restricted__has_delete_permission__override,
     restricted__get_readonly_fields__override,
     restricted__formfield_for_manytomany__override,
     restricted__queryset__override)
from mock import Mock

counter = 0


def create_site(**kwargs):
    global counter
    counter = counter + 1
    defaults = {
        "domain": "domain%d.org" % counter,
        "name": "site%d" % counter,
    }
    defaults.update(kwargs)
    return Site.objects.create(**defaults)


def create_model(**kwargs):
    global counter
    counter = counter + 1
    defaults = {
        "test_field1": "test_field1%d" % counter,
        "test_field2": "test_field2%d" % counter,
    }
    sites = kwargs.get("sites", [])
    del kwargs["sites"]
    defaults.update(kwargs)
    t = TestModel(**defaults)
    t.save()
    t.sites = sites
    t.save()
    return t


def create_user(**kwargs):
    global counter
    counter = counter + 1
    defaults = {
        "username": "username%d" % counter,
        "first_name": "user%d" % counter,
        "last_name": "luser%d" % counter,
        "email": "user%d@luser%d.com" % (counter, counter),
        "password": "password%d" % counter,
    }
    groups = []
    if "groups" in kwargs:
        groups = kwargs["groups"]
        del kwargs["groups"]
    user_permissions = []
    if "user_permissions" in kwargs:
        user_permissions = kwargs["user_permissions"]
        del kwargs["user_permissions"]
    defaults.update(kwargs)
    u = User(**defaults)
    u.save()
    u.groups = groups
    u.user_permissions = user_permissions
    u.save()
    return u


def create_group(**kwargs):
    global counter
    counter = counter + 1
    defaults = {
        "name": "group%d" % counter,
    }
    permissions = []
    if "permissions" in kwargs:
        Permissions = kwargs["permissions"]
        del kwargs["permissions"]
    defaults.update(kwargs)
    g = Group(**defaults)
    g.save()
    g.permissions = permissions
    g.save()
    return g


def create_globalpagepermission(**kwargs):
    sites = []
    if "sites" in kwargs:
        sites = kwargs["sites"]
        del kwargs["sites"]
    gpp = GlobalPagePermission(**kwargs)
    gpp.save()
    gpp.sites = sites
    gpp.save()
    return gpp


class ToBeDecoratedModelAdmin(ModelAdmin):

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        self.test_sites = kwargs['queryset']
        return None

    def queryset(self, restrict_user=False, shared_sites=[],
                 include_orphan=True, **kw):
        return self.model._default_manager.get_query_set()


class TestDecorators(TestCase):

    def _db_field(self):
        class DbField(object):
            name = 'sites'
        return DbField()
    db_field = property(_db_field)

    def setUp(self):
        Site.objects.all().delete()  # delete example.com
        self.main_user = create_user()
        self.site1 = create_site()
        # #settings.__class__.SITE_ID.value = self.site1.id
        self.site2 = create_site()
        self.site3 = create_site()
        self.model = create_model(sites=[self.site1,
                                         self.site2,
                                         self.site3])
        self.request = Mock()

    def set_request_user(self, user=None):
        self.request.user = Mock()
        self.request.user = user or self.main_user

    def test_formfield_m2m_no_restrict_user(self):
        @restricted__formfield_for_manytomany__override(restrict_user=False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        self.set_request_user()
        gpp = create_globalpagepermission(sites=[self.site1,
                                                 self.site2],
                                          user=self.main_user)
        dma = DecoratedModelAdmin(TestModel, admin_site=None)

        dma.formfield_for_manytomany(self.db_field, self.request)

        self.assertQuerysetEqual(
            dma.test_sites,
            [self.site1.id, self.site2.id, self.site3.id],
            lambda o: o.id, ordered=False
        )

    def test_formfield_m2m_restrict_user(self):
        @restricted__formfield_for_manytomany__override(restrict_user=True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        self.set_request_user(self.main_user)
        gpp1 = create_globalpagepermission(sites=[self.site1], user=self.main_user)
        user2 = create_user()
        gpp2 = create_globalpagepermission(sites=[self.site2], user=user2)
        dma = DecoratedModelAdmin(TestModel, admin_site=None)

        dma.formfield_for_manytomany(self.db_field, self.request)

        self.assertQuerysetEqual(
            dma.test_sites,
            [self.site1.id],
            lambda o: o.id
        )

    def test_formfield_m2m_restrict_user_and_user_in_group(self):

        @restricted__formfield_for_manytomany__override(restrict_user=True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        User.objects.all().delete()
        group1 = create_group()
        group2 = create_group()
        self.set_request_user(create_user(groups=[group1]))
        user2 = create_user(groups=[group2])
        gpp1 = create_globalpagepermission(sites=[self.site1], group=group1)
        gpp2 = create_globalpagepermission(sites=[self.site2], group=group2)
        dma = DecoratedModelAdmin(TestModel, admin_site=None)
        dma.formfield_for_manytomany(self.db_field, self.request)
        self.assertQuerysetEqual(
            dma.test_sites,
            [self.site1.id],
            lambda o: o.id
        )

    def test_queryset1(self):
        @restricted__queryset__override(False, False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        model2 = create_model(sites=[self.site1, self.site2, self.site3])
        model3 = create_model(sites=[self.site1, self.site2, self.site3])
        model4 = create_model(sites=[self.site1, self.site2, self.site3])
        self.set_request_user(self.main_user)
        gpp1 = create_globalpagepermission(sites=[self.site1],
                                           user=self.main_user)
        dma = DecoratedModelAdmin(TestModel, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [],
                                 lambda o: o.id, ordered=False)

    def test_queryset2(self):
        @restricted__queryset__override(True, False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        model2 = create_model(sites=[self.site1, self.site2, self.site3])
        model3 = create_model(sites=[self.site1, self.site2, self.site3])
        model4 = create_model(sites=[self.site1, self.site2, self.site3])
        self.set_request_user(self.main_user)
        gpp1 = create_globalpagepermission(sites=[self.site1],
                                           user=self.main_user)
        dma = DecoratedModelAdmin(TestModel, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [self.model.id, model2.id, model3.id, model4.id],
                                 lambda o: o.id, ordered=False)

    def test_queryset3(self):
        @restricted__queryset__override(True, False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        model2 = create_model(sites=[self.site1, self.site2, self.site3])
        model3 = create_model(sites=[self.site1, self.site2, self.site3])
        model4 = create_model(sites=[self.site2, self.site3])
        self.set_request_user(self.main_user)
        gpp1 = create_globalpagepermission(sites=[self.site1],
                                           user=self.main_user)
        dma = DecoratedModelAdmin(TestModel, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [self.model.id, model2.id, model3.id],
                                 lambda o: o.id, ordered=False)

    def test_queryset4(self):
        @restricted__queryset__override(True, False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        self.model.sites = [self.site2, self.site3]
        self.model.save()
        model2 = create_model(sites=[self.site2, self.site3])
        model3 = create_model(sites=[self.site2, self.site3])
        model4 = create_model(sites=[self.site2, self.site3])
        self.set_request_user(self.main_user)
        gpp1 = create_globalpagepermission(sites=[self.site1],
                                           user=self.main_user)
        dma = DecoratedModelAdmin(TestModel, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [],
                                 lambda o: o.id, ordered=False)

    def test_queryset5(self):
        @restricted__queryset__override(True, False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        self.model.sites = [self.site2, self.site3]
        self.model.save()
        model2 = create_model(sites=[self.site2, self.site3])
        model3 = create_model(sites=[self.site2, self.site3])
        model4 = create_model(sites=[self.site2, self.site3])
        model5 = create_model(sites=[self.site2, self.site3], pbs_provided=True)
        self.set_request_user(self.main_user)
        gpp1 = create_globalpagepermission(sites=[self.site1],
                                           user=self.main_user)
        dma = DecoratedModelAdmin(TestModel, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [model5.id],
                                 lambda o: o.id, ordered=False)

    def test_queryset6(self):
        @restricted__queryset__override(True, True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        self.model.sites = [self.site2, self.site3]
        self.model.save()
        model2 = create_model(sites=[self.site2, self.site3])
        model3 = create_model(sites=[self.site2, self.site3])
        model4 = create_model(sites=[self.site2, self.site3])
        model5 = create_model(sites=[])
        self.set_request_user(self.main_user)
        gpp1 = create_globalpagepermission(sites=[self.site1],
                                           user=self.main_user)
        dma = DecoratedModelAdmin(TestModel, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [model5.id],
                                 lambda o: o.id, ordered=False)

    def test_queryset7(self):
        @restricted__queryset__override(True, True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        self.model.sites = [self.site2, self.site3]
        self.model.save()
        model2 = create_model(sites=[self.site2, self.site3])
        model3 = create_model(sites=[self.site2, self.site3])
        model4 = create_model(sites=[self.site2, self.site3], pbs_provided=True)
        model5 = create_model(sites=[])
        self.set_request_user(self.main_user)
        gpp1 = create_globalpagepermission(sites=[self.site1],
                                           user=self.main_user)
        dma = DecoratedModelAdmin(TestModel, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [model4.id, model5.id],
                                 lambda o: o.id, ordered=False)

    def test_queryset7(self):
        @restricted__queryset__override(True, True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        self.model.sites = [self.site2, self.site3]
        self.model.save()
        model2 = create_model(sites=[self.site2, self.site3])
        model3 = create_model(sites=[self.site2, self.site3])
        model4 = create_model(sites=[self.site2, self.site3])
        model5 = create_model(sites=[], pbs_provided=True)
        self.set_request_user(self.main_user)
        gpp1 = create_globalpagepermission(sites=[self.site1],
                                           user=self.main_user)
        dma = DecoratedModelAdmin(TestModel, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [model5.id],
                                 lambda o: o.id, ordered=False)

    def test_queryset8(self):
        @restricted__queryset__override(True, True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        self.model.sites = [self.site2, self.site3]
        self.model.save()
        model2 = create_model(sites=[self.site2, self.site3])
        model3 = create_model(sites=[self.site2, self.site3])
        model4 = create_model(sites=[self.site2, self.site3], pbs_provided=True)
        model5 = create_model(sites=[], pbs_provided=True)
        self.set_request_user(self.main_user)
        gpp1 = create_globalpagepermission(sites=[self.site1],
                                           user=self.main_user)
        dma = DecoratedModelAdmin(TestModel, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [model4.id, model5.id],
                                 lambda o: o.id, ordered=False)

    def test_queryset9(self):
        @restricted__queryset__override(True, False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        self.model.sites = [self.site2, self.site3]
        self.model.save()
        model2 = create_model(sites=[self.site2, self.site3])
        model3 = create_model(sites=[self.site2, self.site3])
        model4 = create_model(sites=[self.site2, self.site3], pbs_provided=True)
        model5 = create_model(sites=[])
        self.set_request_user(self.main_user)
        gpp1 = create_globalpagepermission(sites=[self.site1],
                                           user=self.main_user)
        dma = DecoratedModelAdmin(TestModel, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [model4.id],
                                 lambda o: o.id, ordered=False)

    def test_queryset10(self):
        @restricted__queryset__override(True, False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        self.model.sites = [self.site2, self.site3]
        self.model.save()
        model2 = create_model(sites=[self.site2, self.site3])
        model3 = create_model(sites=[self.site2, self.site3])
        model4 = create_model(sites=[self.site2, self.site3], pbs_provided=True)
        model5 = create_model(sites=[])
        super_user = create_user(is_superuser=True)
        self.set_request_user(super_user)
        gpp1 = create_globalpagepermission(sites=[self.site1],
                                           user=self.main_user)
        dma = DecoratedModelAdmin(TestModel, admin_site=None)

        self.assertQuerysetEqual(dma.queryset(self.request),
                                 TestModel.objects.values_list('id', flat=True),
                                 lambda o: o.id, ordered=False)

    def test_queryset11(self):
        @restricted__queryset__override(restrict_user=True,
                             include_orphan=False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        model2 = create_model(sites=[self.site2, self.site3])
        model3 = create_model(sites=[self.site3])
        group1 = create_group()
        self.set_request_user(create_user(groups=[group1]))
        gpp1 = create_globalpagepermission(sites=[self.site1], group=group1)
        dma = DecoratedModelAdmin(TestModel, admin_site=None)
        self.assertQuerysetEqual(dma.queryset(self.request),
                                 [self.model.id],
                                 lambda o: o.id)

    def test_get_readonly_fields1(self):
        allways_ro=['publish_date']
        @restricted__get_readonly_fields__override(restrict_user=False, allways_ro=allways_ro)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        self.set_request_user(self.main_user)
        dma = DecoratedModelAdmin(TestModel, admin_site=None)
        self.assertEquals(dma.get_readonly_fields(self.request), ['publish_date'])

    def test_get_readonly_fields2(self):
        allways_ro=['publish_date']
        @restricted__get_readonly_fields__override(restrict_user=False, allways_ro=allways_ro)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        self.set_request_user(self.main_user)

        dma = DecoratedModelAdmin(TestModel, admin_site=None)
        self.assertEquals(dma.get_readonly_fields(self.request, self.model),\
                          ['publish_date', 'pbs_provided', 'read_only'])

    def test_get_readonly_fields3(self):
        allways_ro=['publish_date']
        @restricted__get_readonly_fields__override(restrict_user=True, allways_ro=allways_ro)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        self.set_request_user(self.main_user)

        dma = DecoratedModelAdmin(TestModel, admin_site=None)
        self.assertEquals(dma.get_readonly_fields(self.request, self.model),\
                          ['publish_date', 'pbs_provided', 'read_only'])

    def test_get_readonly_fields4(self):
        allways_ro=['publish_date']
        @restricted__get_readonly_fields__override(restrict_user=True, allways_ro=allways_ro)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        self.set_request_user(self.main_user)
        self.model.pbs_provided = True
        self.model.save()
        dma = DecoratedModelAdmin(TestModel, admin_site=None)
        self.assertEquals(dma.get_readonly_fields(self.request, self.model),\
                          self.model._meta.get_all_field_names())

    def test_get_readonly_fields5(self):
        allways_ro=['publish_date']
        @restricted__get_readonly_fields__override(restrict_user=True, allways_ro=allways_ro)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass

        self.main_user.is_superuser = True
        self.main_user.save()
        self.set_request_user(self.main_user)
        self.model.pbs_provided = True
        self.model.save()
        dma = DecoratedModelAdmin(TestModel, admin_site=None)
        self.assertEquals(dma.get_readonly_fields(self.request, self.model),\
                          ['publish_date'])

    def test_has_delete_permission1(self):
        @restricted__has_delete_permission__override(restrict_user=False)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass
        self.set_request_user(self.main_user)
        dma = DecoratedModelAdmin(TestModel, admin_site=None)
        self.assertEquals(dma.has_delete_permission(self.request), True)

    def test_has_delete_permission2(self):
        @restricted__has_delete_permission__override(restrict_user=True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass
        self.set_request_user(self.main_user)

        deleted_model1 = create_model(sites=[self.site1])
        deleted_model2 = create_model(sites=[self.site1])
        self.request.POST = Mock()
        self.request.POST.getlist.return_value = [deleted_model1.id, deleted_model2.id]

        dma = DecoratedModelAdmin(TestModel, admin_site=None)
        #we CAN delete the created models because neither of them are pbs_provided nor readonly
        self.assertEquals(dma.has_delete_permission(self.request), True)

    def test_has_delete_permission3(self):
        @restricted__has_delete_permission__override(restrict_user=True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass
        self.set_request_user(self.main_user)

        deleted_model1 = create_model(sites=[self.site1])
        deleted_model2 = create_model(sites=[self.site1], pbs_provided=True)
        self.request.POST = Mock()
        self.request.POST.getlist.return_value = [deleted_model1.id, deleted_model2.id]

        dma = DecoratedModelAdmin(TestModel, admin_site=None)
        #we CANNOT delete the created models because deleted_model2 is pbs_provided
        #  and the user is not superuser
        self.assertEquals(dma.has_delete_permission(self.request), False)

    def test_has_delete_permission4(self):
        @restricted__has_delete_permission__override(restrict_user=True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass
        self.set_request_user(self.main_user)

        deleted_model1 = create_model(sites=[self.site1])
        deleted_model2 = create_model(sites=[self.site1], read_only=True)
        self.request.POST = Mock()
        self.request.POST.getlist.return_value = [deleted_model1.id, deleted_model2.id]

        dma = DecoratedModelAdmin(TestModel, admin_site=None)
        #we CANNOT delete the created models because deleted_model2 is read_only
        #  and the user is not superuser
        self.assertEquals(dma.has_delete_permission(self.request), False)

    def test_has_delete_permission5(self):
        @restricted__has_delete_permission__override(restrict_user=True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass
        self.set_request_user(self.main_user)

        deleted_model1 = create_model(sites=[self.site1])
        deleted_model2 = create_model(sites=[self.site1], read_only=True)
        self.request.POST = Mock()
        self.request.POST.getlist.return_value = [deleted_model1.id]

        dma = DecoratedModelAdmin(TestModel, admin_site=None)
        #deleted_model1 CAN be as its the only one in the list
        self.assertEquals(dma.has_delete_permission(self.request), True)

    def test_has_delete_permission6(self):
        @restricted__has_delete_permission__override(restrict_user=True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass
        self.set_request_user(self.main_user)

        deleted_model1 = create_model(sites=[self.site1])
        deleted_model2 = create_model(sites=[self.site1], read_only=True)

        dma = DecoratedModelAdmin(TestModel, admin_site=None)
        self.assertEquals(dma.has_delete_permission(self.request, deleted_model1), True)

    def test_has_delete_permission7(self):
        @restricted__has_delete_permission__override(restrict_user=True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass
        self.set_request_user(self.main_user)

        deleted_model1 = create_model(sites=[self.site1])
        deleted_model2 = create_model(sites=[self.site1], read_only=True)

        dma = DecoratedModelAdmin(TestModel, admin_site=None)
        self.assertEquals(dma.has_delete_permission(self.request, deleted_model2), False)

    def test_has_delete_permission8(self):
        @restricted__has_delete_permission__override(restrict_user=True)
        class DecoratedModelAdmin(ToBeDecoratedModelAdmin):
            pass
        self.main_user.is_superuser = True
        self.main_user.save()
        self.set_request_user(self.main_user)

        deleted_model1 = create_model(sites=[self.site1])
        deleted_model2 = create_model(sites=[self.site1], read_only=True)
        self.request.POST = Mock()
        self.request.POST.getlist.return_value = [deleted_model1.id, deleted_model2.id]

        dma = DecoratedModelAdmin(TestModel, admin_site=None)
        #super_user can delete anything
        self.assertEquals(dma.has_delete_permission(self.request), True)
