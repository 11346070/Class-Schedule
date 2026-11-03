from django.db import migrations, models
import django.db.models.deletion


def link_teachers(apps, schema_editor):
    Teacher = apps.get_model("timetable", "Teacher")
    Course = apps.get_model("timetable", "Course")
    teachers = {item.name: item for item in Teacher.objects.all()}
    for course in Course.objects.all():
        label = (course.teacher_name or "").strip()
        if not label:
            continue
        teacher = teachers.get(label)
        if teacher is None:
            teacher = Teacher.objects.create(name=label)
            teachers[label] = teacher
        course.teacher = teacher
        course.save(update_fields=["teacher"])


class Migration(migrations.Migration):

    dependencies = [
        ("timetable", "0014_schoolclass_relation"),
    ]

    operations = [
        migrations.CreateModel(
            name="Teacher",
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
                ("name", models.CharField(max_length=50, unique=True, verbose_name="教師姓名")),
            ],
            options={
                "verbose_name": "教師",
                "verbose_name_plural": "教師",
                "ordering": ["name"],
            },
        ),
        migrations.RenameField(
            model_name="course",
            old_name="teacher",
            new_name="teacher_name",
        ),
        migrations.AddField(
            model_name="course",
            name="teacher",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="courses",
                to="timetable.teacher",
                verbose_name="授課教師",
            ),
        ),
        migrations.RunPython(link_teachers, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="course",
            name="teacher_name",
        ),
    ]
