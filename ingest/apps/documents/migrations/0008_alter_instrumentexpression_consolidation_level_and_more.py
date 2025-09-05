# Generated manually for InstrumentExpression field updates

from django.db import migrations, models
import django.db.models.deletion
import ingest.apps.documents.enums


class Migration(migrations.Migration):

    dependencies = [
        ('masterdata', '0001_initial'),
        ('documents', '0007_alter_historicalinstrumentwork_eli_uri_work_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instrumentexpression',
            name='consolidation_level',
            field=models.CharField(choices=[('base', 'پایه'), ('consolidated', 'تجمیع شده'), ('annotated', 'حاشیه نویسی')], default=ingest.apps.documents.enums.ConsolidationLevel['BASE'], max_length=20, verbose_name='سطح تلفیق'),
        ),
        migrations.AlterField(
            model_name='instrumentexpression',
            name='language',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='masterdata.language', verbose_name='زبان'),
        ),
        migrations.AlterField(
            model_name='historicalinstrumentexpression',
            name='consolidation_level',
            field=models.CharField(choices=[('base', 'پایه'), ('consolidated', 'تجمیع شده'), ('annotated', 'حاشیه نویسی')], default=ingest.apps.documents.enums.ConsolidationLevel['BASE'], max_length=20, verbose_name='سطح تلفیق'),
        ),
        migrations.AlterField(
            model_name='historicalinstrumentexpression',
            name='language',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='masterdata.language', verbose_name='زبان'),
        ),
    ]
