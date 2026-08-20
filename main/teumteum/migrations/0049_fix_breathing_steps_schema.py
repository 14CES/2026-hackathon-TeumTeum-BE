# id=1, id=2는 제일 처음 시드 마이그레이션(0017)에서 만들어진 이후로 스키마가 업데이트 안 되고
# {"phase": ..., "duration_seconds": ...} 형태로 남아있었다. 다른 모든 audio_guide/stretch_guide는
# {"order": ..., "instruction": ..., "duration_seconds": ...} 형태라서, 프론트가 instruction을 읽는다면
# 이 두 모듈만 안내 문구 없이 빈 화면으로 시간만 흐르게 된다. order/instruction 형태로 맞춘다.

from django.db import migrations


def fix_breathing_steps(apps, schema_editor):
    ActivityModuleTemplate = apps.get_model("teumteum", "ActivityModuleTemplate")

    steps_by_id = {
        1: [
            {"order": 1, "instruction": "화면에서 시선을 떼고 코로 천천히 숨을 들이마셔요.", "duration_seconds": 4},
            {"order": 2, "instruction": "먼 곳을 바라보며 입으로 길게 내쉬어요.", "duration_seconds": 6},
        ],
        2: [
            {"order": 1, "instruction": "코로 천천히 숨을 들이마셔요.", "duration_seconds": 4},
            {"order": 2, "instruction": "긴장을 내려놓듯 길게 내쉬어요.", "duration_seconds": 6},
        ],
    }

    for template_id, steps in steps_by_id.items():
        ActivityModuleTemplate.objects.filter(id=template_id).update(steps=steps)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('teumteum', '0048_backfill_course_content_types'),
    ]

    operations = [
        migrations.RunPython(fix_breathing_steps, noop),
    ]
