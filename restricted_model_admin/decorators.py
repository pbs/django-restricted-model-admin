from django.contrib.sites.models import Site
from django.db.models import Q, Model
from django.contrib.admin.options import ModelAdmin
from django.utils.translation import ugettext_lazy as _


def restricted_overrides(restrict_user=False, include_orphan=True, allways_ro=(), **kw):

    def _restricted_decorators(cls):
        cls = restricted__formfield_for_manytomany__override(restrict_user)(cls)
        cls = restricted__queryset__override(restrict_user, include_orphan)(cls)
        cls = restricted__get_readonly_fields__override(restrict_user, allways_ro)(cls)
        cls = restricted__has_delete_permission__override(restrict_user)(cls)
        cls = restricted__change_view__override(restrict_user)(cls)
        return cls

    return _restricted_decorators


def append_restricted_fields(cls):
    append_admin_fields(cls, ('pbs_provided', 'read_only'))
    return cls


def append_pbs_enabled_field(cls):
    append_admin_fields(cls, ('pbs_provided', ))
    return cls


def append_admin_fields(cls, fields):
    if cls.fieldsets:
        base_fieldsets = [f for f in cls.fieldsets]
        pbs_fieldsets = [(_('PBS'), {
            'fields': (fields,),
            'classes': ('collapse',),
        })]
        cls.fieldsets = tuple(base_fieldsets + pbs_fieldsets)


def throw_error_if_not_ModelAdmin(f):
    def _inner(*args, **kwargs):
        cls = args[0]
        if not issubclass(cls, ModelAdmin):
            raise TypeError('%s should be an subclass of ModelAdmin' % cls.__name__)
        return f(*args, **kwargs)
    return _inner


def restricted__formfield_for_manytomany__override(restrict_user=False, **kw):
    """Parameterized class decorator used to extend the default "formfield_for_manytomany" behavior of a ModelAdmin derived class.
    """
    @throw_error_if_not_ModelAdmin
    def _formfield_for_manytomany(cls):

        def __formfield_for_manytomany(self, db_field, request, **kwargs):
            if db_field.name == "sites":
                f = Q()
                if restrict_user and not request.user.is_superuser:
                    f |= Q(globalpagepermission__user=request.user)
                    f |= Q(globalpagepermission__group__user=request.user)
                kwargs["queryset"] = Site.objects.filter(f).distinct()
            return (super(cls, self)
                    .formfield_for_manytomany(db_field, request, **kwargs))

        cls.formfield_for_manytomany = __formfield_for_manytomany
        return cls
    return _formfield_for_manytomany


def restricted__queryset__override(restrict_user=False, include_orphan=True, **kw):
    """Parameterized class decorator used to extend the default "queryset" behavior of a ModelAdmin derived class.
    """
    @throw_error_if_not_ModelAdmin
    def _queryset(cls):

        def __queryset(self, request):
            q = super(cls, self).queryset(request)
            f = Q()
            if not request.user.is_superuser:
                if restrict_user:
                    f |= Q(sites__globalpagepermission__user=request.user)
                    f |= Q(sites__globalpagepermission__group__user=request.user)
                if 'pbs_provided' in self.model._meta.get_all_field_names():
                    f |= Q(pbs_provided=True)

                if include_orphan:
                    f |= Q(sites__isnull=True)
            return q.filter(f).distinct()

        cls.queryset = __queryset
        return cls

    return _queryset


def restricted__get_readonly_fields__override(restrict_user=False, allways_ro=(), shared_and_readonly=True,**kw):
    """Parameterized class decorator used to extend the default "get_readonly_fields" behavior of a ModelAdmin derived class.
    """
    @throw_error_if_not_ModelAdmin
    def _get_readonly_fields(cls):

        def __get_readonly_fields(self, request, obj=None):
            if request.user.is_superuser:
                return allways_ro
            if not obj:
                return  self.model().get_readonly_fields_for_stuff_users()
            if restrict_user and ro_state(obj, shared_and_readonly):
                # return all fields
                return obj._meta.get_all_field_names()
            return obj.get_readonly_fields_for_stuff_users()

        cls.get_readonly_fields = __get_readonly_fields
        return cls

    return _get_readonly_fields


def restricted__has_delete_permission__override(restrict_user=False, shared_and_readonly=True, **kw):
    """Parameterized class decorator used to extend the default "has_delete_permission" behavior of a ModelAdmin derived class.
    """
    @throw_error_if_not_ModelAdmin
    def _has_delete_permission(cls):

        def __has_delete_permission(self, request, obj=None):
            if request.user.is_superuser:
                return True
            if restrict_user:
                if not obj:
                    #here multiple objects have been selected for deletion
                    objs = get_objects_to_bo_deleted(self.model, request)
                    return not any([ro_state(o, shared_and_readonly) for o in objs])
                if ro_state(obj, shared_and_readonly):
                    return False
            return True

        cls.has_delete_permission = __has_delete_permission
        return cls
    return _has_delete_permission


def restricted__change_view__override(restrict_user=False, shared_and_readonly=True, **kw):
    """Parameterized class decorator used to exted the default "change_view" behavior of a ModelAdmin derived class.
    """
    @throw_error_if_not_ModelAdmin
    def _change_view(cls):

        def __change_view(self, request, object_id, extra_context=None):
            extra_context = {}
            if not request.user.is_superuser:
                obj = self.model.objects.get(pk=object_id)
                if restrict_user and ro_state(obj, shared_and_readonly):
                    extra_context = {'read_only': True}
            return super(cls, self).change_view(request,
                        object_id, extra_context=extra_context)

        cls.change_view = __change_view
        return cls
    return _change_view


def ro_state(obj, shared_and_readonly):
    #checks to determine if the state of the obj should be readonly
    read_only = getattr(obj, "read_only", False)
    pbs_provided = getattr(obj, "pbs_provided", False)
    return read_only or (pbs_provided and shared_and_readonly)


def get_objects_to_bo_deleted(model, request):
    return model.objects.filter(id__in=request.POST.getlist('_selected_action', []))