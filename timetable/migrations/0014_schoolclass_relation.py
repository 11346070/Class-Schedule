from django.db import migrations, models
import django.db.models.deletion


def rebuild_schoolclass(apps, schema_editor):
    """班級主鍵改為編號，名稱就可以修改，課程和學生不會因此對不上。"""
    schema_editor.execute(
        """
        CREATE TABLE "timetable_schoolclass_new" (
            "id" integer NOT NULL PRIMARY KEY AUTOINCREMENT,
            "name" varchar(50) NOT NULL UNIQUE
        )
        """
    )
    schema_editor.execute(
        """
        INSERT INTO "timetable_schoolclass_new" ("name")
        SELECT "name" FROM "timetable_schoolclass"
        """
    )
    schema_editor.execute('DROP TABLE "timetable_schoolclass"')
    schema_editor.execute(
        'ALTER TABLE "timetable_schoolclass_new" RENAME TO "timetable_schoolclass"'
    )


def link_classes(apps, schema_editor):
    SchoolClass = apps.get_model("timetable", "SchoolClass")
    Course = apps.get_model("timetable", "Course")
    StudentProfile = apps.get_model("timetable", "StudentProfile")
    classes = {item.name: item for item in SchoolClass.objects.all()}

    def klass(name):
        name = (name or "").strip()
        if not name or name == "全校":
            return None
        found = classes.get(name)
        if found is None:
            found = SchoolClass.objects.create(name=name)
            classes[name] = found
        return found

    for course in Course.objects.all():
        label = (course.target_class or "").strip()
        course.opens_to_all = label == "全校"
        course.school_class = None if label == "全校" else klass(label)
        course.save(update_fields=["opens_to_all", "school_class"])

    for profile in StudentProfile.objects.all():
        profile.school_class = klass(profile.class_name)
        profile.save(update_fields=["school_class"])


class Migration(migrations.Migration):

    dependencies = [
        ("timetable", "0013_schoolclass"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunPython(rebuild_schoolclass, migrations.RunPython.noop),
            ],
            state_operations=[
                migrations.DeleteModel(name="SchoolClass"),
                migrations.CreateModel(
                    name="SchoolClass",
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
                        (
                            "name",
                            models.CharField(max_length=50, unique=True, verbose_name="班級名稱"),
                        ),
                    ],
                    options={
                        "verbose_name": "班級",
                        "verbose_name_plural": "班級",
                        "ordering": ["name"],
                    },
                ),
            ],
        ),
        migrations.AddField(
            model_name="course",
            name="opens_to_all",
            field=models.BooleanField(default=False, verbose_name="開放全校"),
        ),
        migrations.AddField(
            model_name="course",
            name="school_class",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="courses",
                to="timetable.schoolclass",
                verbose_name="開課班級",
            ),
        ),
        migrations.AddField(
            model_name="studentprofile",
            name="school_class",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="students",
                to="timetable.schoolclass",
                verbose_name="班級",
            ),
        ),
        migrations.RunPython(link_classes, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="course",
            name="target_class",
        ),
        migrations.RemoveField(
            model_name="studentprofile",
            name="class_name",
        ),
    ]
