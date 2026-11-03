from django.db import migrations, models
import django.db.models.deletion


def attach_current_semester(apps, schema_editor):
    Semester = apps.get_model("timetable", "Semester")
    Course = apps.get_model("timetable", "Course")
    semester, _created = Semester.objects.get_or_create(
        code="本學期",
        defaults={"name": "本學期", "is_current": True},
    )
    Course.objects.filter(semester__isnull=True).update(semester=semester)


class Migration(migrations.Migration):

    dependencies = [
        ("timetable", "0017_course_meeting"),
    ]

    operations = [
        migrations.CreateModel(
            name="Semester",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("code", models.CharField(max_length=20, unique=True, verbose_name="學期代碼")),
                ("name", models.CharField(blank=True, default="", max_length=50, verbose_name="學期名稱")),
                ("is_current", models.BooleanField(default=False, verbose_name="目前學期")),
            ],
            options={
                "verbose_name": "學期",
                "verbose_name_plural": "學期",
                "ordering": ["-is_current", "code"],
            },
        ),
        migrations.AddField(
            model_name="course",
            name="semester",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="courses",
                to="timetable.semester",
                verbose_name="學期",
            ),
        ),
        migrations.RunPython(attach_current_semester, migrations.RunPython.noop),
    ]
