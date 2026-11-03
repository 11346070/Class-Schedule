from django.db import migrations, models


def seed_school_classes(apps, schema_editor):
    SchoolClass = apps.get_model("timetable", "SchoolClass")
    Course = apps.get_model("timetable", "Course")
    StudentProfile = apps.get_model("timetable", "StudentProfile")
    names = set()
    for raw in Course.objects.values_list("target_class", flat=True):
        name = (raw or "").strip()
        if name and name != "全校":
            names.add(name)
    for raw in StudentProfile.objects.values_list("class_name", flat=True):
        name = (raw or "").strip()
        if name and name != "全校":
            names.add(name)
    SchoolClass.objects.bulk_create([SchoolClass(name=name) for name in sorted(names)])


class Migration(migrations.Migration):

    dependencies = [
        ("timetable", "0012_course_type_choices"),
    ]

    operations = [
        migrations.CreateModel(
            name="SchoolClass",
            fields=[
                ("name", models.CharField(max_length=50, primary_key=True, serialize=False, verbose_name="班級名稱")),
            ],
            options={
                "verbose_name": "班級",
                "verbose_name_plural": "班級",
                "ordering": ["name"],
            },
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="schedule_note",
            field=models.TextField(blank=True, default="", verbose_name="課表提醒"),
        ),
        migrations.RunPython(seed_school_classes, migrations.RunPython.noop),
    ]
