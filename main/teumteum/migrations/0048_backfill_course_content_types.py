# content_types 필드가 생기기 전에 만들어진 옛날 Course들을 위한 백필.
# 각 Course가 만들어진 시점 기준으로 그 유저가 마지막으로 답했던 MainAnswer를 찾아서
# 그때 고른 회복 방식을 그대로 채워넣는다 (라이브로 저장됐다면 나왔을 값과 동일).
# 매칭되는 MainAnswer가 없으면 손대지 않고 건너뛴다.

from django.db import migrations


def backfill_content_types(apps, schema_editor):
    Course = apps.get_model("teumteum", "Course")
    MainAnswer = apps.get_model("teumteum", "MainAnswer")
    Record = apps.get_model("records", "Record")

    courses = Course.objects.filter(content_types=[])

    for course in courses:
        main_answer = (
            MainAnswer.objects
            .filter(user_id=course.user_id, created_at__lte=course.created_at)
            .order_by("-created_at")
            .first()
        )

        if not main_answer:
            continue

        content_types = list(
            main_answer.preferred_options.values_list("content", flat=True)
        )

        if not content_types:
            continue

        course.content_types = content_types
        course.save(update_fields=["content_types"])

        Record.objects.filter(course_id=course.id).update(
            category=",".join(content_types)
        )


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('teumteum', '0047_course_content_types'),
        ('records', '0004_record_ai_title'),
    ]

    operations = [
        migrations.RunPython(backfill_content_types, noop),
    ]
