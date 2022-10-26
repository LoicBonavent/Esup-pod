import random
import string
import re

from django import forms
from django.conf import settings
from django.contrib.sites.models import Site
from django.db.models.query import QuerySet
from django.utils.translation import ugettext_lazy as _
from django.core.exceptions import ValidationError
from django_select2 import forms as s2forms
from django.contrib.admin import widgets as admin_widgets
from django.utils import timezone

from django.forms import CharField, Textarea
from django.core.validators import validate_email

from pod.main.forms_utils import add_placeholder_and_asterisk
from .models import Meeting

MEETING_MAIN_FIELDS = getattr(
    settings,
    "MEETING_MAIN_FIELDS",
    (
        "name",
        "owner",
        "additional_owners",
        "attendee_password",
        "is_restricted",
        "restrict_access_to_groups",
        "start",
        "start_time",
        "expected_duration",
    )
)
MEETING_RECURRING_FIELDS = getattr(
    settings,
    "MEETING_RECURRING_FIELDS",
    (
        "recurrence",
        "frequency",
        "recurring_until",
        "nb_occurrences",
        "weekdays",
        "monthly_type"
    )
)
MEETING_DISABLE_RECORD = getattr(settings, "MEETING_DISABLE_RECORD", True)

MEETING_RECORD_FIELDS = getattr(
    settings,
    "MEETING_RECORD_FIELDS",
    ("record", "auto_start_recording", "allow_start_stop_recording"),
)

if MEETING_DISABLE_RECORD:
    MEETING_EXCLUDE_FIELDS = MEETING_MAIN_FIELDS + MEETING_RECURRING_FIELDS + ("id",) + MEETING_RECORD_FIELDS
else:
    MEETING_EXCLUDE_FIELDS = MEETING_MAIN_FIELDS + MEETING_RECURRING_FIELDS + ("id",)

for field in Meeting._meta.fields:
    # print(field.name, field.editable)
    if field.editable is False:
        MEETING_EXCLUDE_FIELDS = MEETING_EXCLUDE_FIELDS + (field.name,)


def get_meeting_fields():
    fields = []
    for field in Meeting._meta.fields:
        if field.name not in MEETING_EXCLUDE_FIELDS:
            fields.append(field.name)
    return fields


def get_random_string(length):
    # choose from all lowercase letter
    letters = string.ascii_lowercase
    result_str = "".join(random.choice(letters) for i in range(length))
    return result_str


class OwnerWidget(s2forms.ModelSelect2Widget):
    search_fields = [
        "username__icontains",
        "email__icontains",
    ]


class AddOwnerWidget(s2forms.ModelSelect2MultipleWidget):
    search_fields = [
        "username__icontains",
        "email__icontains",
    ]


class MeetingForm(forms.ModelForm):
    site = forms.ModelChoiceField(Site.objects.all(), required=False)
    required_css_class = "required"
    is_admin = False
    is_superuser = False

    expected_duration = forms.IntegerField(
        label=_("Duration"),
        initial=2,
        max_value=5,
        min_value=1,
        help_text=_("Specify a duration in hour between 1 and 5 hours")
    )

    fieldsets = (
        (None, {"fields": MEETING_MAIN_FIELDS}),
        (
            "recurring_options",
            {
                "legend": _("Recurring options"),
                "classes": "modal",
                "fields": MEETING_RECURRING_FIELDS,
            },
        ),
        (
            "advanced_options",
            {
                "legend": _("Advanced options"),
                "classes": "collapse",
                "fields": get_meeting_fields(),
            },
        ),
    )

    def filter_fields_admin(form):
        if form.is_superuser is False and form.is_admin is False:
            form.remove_field("owner")

        if not hasattr(form, "admin_form"):
            form.remove_field("site")

    def clean(self):
        cleaned_data = super(MeetingForm, self).clean()
        if "expected_duration" in cleaned_data.keys():
            self.cleaned_data["expected_duration"] = timezone.timedelta(
                hours=self.cleaned_data["expected_duration"]
            )

        if (
            "start" in cleaned_data.keys()
            and "recurring_until" in cleaned_data.keys()
            and cleaned_data["recurring_until"] is not None
            and cleaned_data["start"] > cleaned_data["recurring_until"]
        ):
            raise ValidationError(_("Start date must be less than recurring until date"))
        if "additional_owners" in cleaned_data.keys() and isinstance(
            self.cleaned_data["additional_owners"], QuerySet
        ):
            meetingowner = (
                self.instance.owner
                if hasattr(self.instance, "owner")
                else cleaned_data["owner"]
                if "owner" in cleaned_data.keys()
                else self.current_user
            )
            if (
                meetingowner
                and meetingowner in self.cleaned_data["additional_owners"].all()
            ):
                raise ValidationError(
                    _("Owner of the video cannot be an additional owner too")
                )
        if (
            "restrict_access_to_groups" in cleaned_data.keys()
            and len(cleaned_data["restrict_access_to_groups"]) > 0
        ):
            cleaned_data["is_restricted"] = True
        if "voice_bridge" in cleaned_data.keys() and cleaned_data[
            "voice_bridge"
        ] not in range(10000, 99999):
            raise ValidationError(
                _("Voice bridge must be a 5-digit number in the range 10000 to 99999")
            )

    def __init__(self, *args, **kwargs):

        self.is_staff = (
            kwargs.pop("is_staff") if "is_staff" in kwargs.keys() else self.is_staff
        )

        self.is_superuser = (
            kwargs.pop("is_superuser")
            if ("is_superuser" in kwargs.keys())
            else self.is_superuser
        )
        self.current_lang = kwargs.pop("current_lang", settings.LANGUAGE_CODE)
        self.current_user = kwargs.pop("current_user", None)
        super(MeetingForm, self).__init__(*args, **kwargs)
        self.set_queryset()
        self.filter_fields_admin()
        # Manage required fields html
        self.fields = add_placeholder_and_asterisk(self.fields)
        if self.fields.get("owner"):
            self.fields["owner"].queryset = self.fields["owner"].queryset.filter(
                owner__sites=Site.objects.get_current()
            )
        # self.fields.get("attendee_password"):
        if not self.initial.get("attendee_password"):
            self.initial["attendee_password"] = get_random_string(8)

        if self.initial.get("expected_duration"):
            self.initial["expected_duration"] = int(
                self.initial.get("expected_duration").seconds / 3600
            )

        # MEETING_DISABLE_RECORD
        if MEETING_DISABLE_RECORD:
            for field in MEETING_RECORD_FIELDS:
                self.remove_field(field)

    def remove_field(self, field):
        if self.fields.get(field):
            del self.fields[field]

    def set_queryset(self):
        # if self.current_user is not None:
        #    users_groups = self.current_user.owner.accessgroup_set.all()
        self.fields["restrict_access_to_groups"].queryset = self.fields[
            "restrict_access_to_groups"
        ].queryset.filter(sites=Site.objects.get_current())

    class Meta(object):
        model = Meeting
        fields = "__all__"
        widgets = {
            "owner": OwnerWidget,
            "additional_owners": AddOwnerWidget,
            "start": admin_widgets.AdminDateWidget,
            "recurring_until": admin_widgets.AdminDateWidget,
        }


class MeetingDeleteForm(forms.Form):
    agree = forms.BooleanField(
        label=_("I agree"),
        help_text=_("Delete meeting cannot be undone"),
        widget=forms.CheckboxInput(),
    )

    def __init__(self, *args, **kwargs):
        super(MeetingDeleteForm, self).__init__(*args, **kwargs)
        self.fields = add_placeholder_and_asterisk(self.fields)


class MeetingPasswordForm(forms.Form):
    name = forms.CharField(label=_("Name"))
    password = forms.CharField(label=_("Password"), widget=forms.PasswordInput())

    def __init__(self, *args, **kwargs):
        self.current_user = kwargs.pop("current_user", None)
        self.remove_password = kwargs.pop("remove_password", None)
        super(MeetingPasswordForm, self).__init__(*args, **kwargs)
        self.fields = add_placeholder_and_asterisk(self.fields)
        if self.current_user:
            self.remove_field("name")
        if self.remove_password:
            self.remove_field("password")

    def remove_field(self, field):
        if self.fields.get(field):
            del self.fields[field]


class EmailsListField(CharField):
    widget = Textarea

    def clean(self, value):
        super(EmailsListField, self).clean(value)

        emails = re.compile(r"[^\w\.\-\+@_]+").split(value)

        if not emails:
            raise ValidationError(_("Enter at least one e-mail address."))

        for email in emails:
            if email != "":
                validate_email(email)
            else:
                emails.remove(email)

        return emails


class MeetingInviteForm(forms.Form):
    emails = EmailsListField(
        label=_("Emails"),
        help_text=_("You can fill one email adress per line"),
    )

    def __init__(self, *args, **kwargs):
        super(MeetingInviteForm, self).__init__(*args, **kwargs)
        self.fields = add_placeholder_and_asterisk(self.fields)
