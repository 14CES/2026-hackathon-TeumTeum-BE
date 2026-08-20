# "이 틈이 끝나면 무엇을 하나요?" -> "틈이 끝나면 무엇을 하나요?" (프론트 요청으로 "이" 제거)

from django.db import migrations


def fix_title(apps, schema_editor):
    Question = apps.get_model("teumteum", "Question")
    Question.objects.filter(question_id=3).update(title="틈이 끝나면 무엇을 하나요?")


def revert_title(apps, schema_editor):
    Question = apps.get_model("teumteum", "Question")
    Question.objects.filter(question_id=3).update(title="이 틈이 끝나면 무엇을 하나요?")


class Migration(migrations.Migration):

    dependencies = [
        ('teumteum', '0049_fix_breathing_steps_schema'),
    ]

    operations = [
        migrations.RunPython(fix_title, revert_title),
    ]
