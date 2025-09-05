# Generated manually for InstrumentWork field updates

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masterdata', '0001_initial'),
        ('documents', '0004_historicalingestlog_historicalinstrumentrelation_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='instrumentwork',
            name='eli_uri_work',
            field=models.URLField(blank=True, help_text='urn:lex:ir:<authority>:<doc_type>:<yyyy-mm-dd>:<number><br>مثال: urn:lex:ir:majlis:law:2020-06-01:123', verbose_name='ELI URI اثر'),
        ),
        migrations.AlterField(
            model_name='instrumentwork',
            name='primary_language',
            field=models.ForeignKey(blank=True, default=None, null=True, on_delete=django.db.models.deletion.SET_NULL, to='masterdata.language', verbose_name='زبان اصلی'),
        ),
        migrations.AlterField(
            model_name='instrumentwork',
            name='urn_lex',
            field=models.CharField(blank=True, help_text='https://<domain>/<country>/<type>/<year>/<number><br>مثال: https://laws.example.ir/ir/act/2020/123', max_length=200, verbose_name='URN LEX'),
        ),
        migrations.AlterField(
            model_name='historicalinstrumentwork',
            name='eli_uri_work',
            field=models.URLField(blank=True, help_text='urn:lex:ir:<authority>:<doc_type>:<yyyy-mm-dd>:<number><br>مثال: urn:lex:ir:majlis:law:2020-06-01:123', verbose_name='ELI URI اثر'),
        ),
        migrations.AlterField(
            model_name='historicalinstrumentwork',
            name='primary_language',
            field=models.ForeignKey(blank=True, db_constraint=False, default=None, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='masterdata.language', verbose_name='زبان اصلی'),
        ),
        migrations.AlterField(
            model_name='historicalinstrumentwork',
            name='urn_lex',
            field=models.CharField(blank=True, help_text='https://<domain>/<country>/<type>/<year>/<number><br>مثال: https://laws.example.ir/ir/act/2020/123', max_length=200, verbose_name='URN LEX'),
        ),
    ]
