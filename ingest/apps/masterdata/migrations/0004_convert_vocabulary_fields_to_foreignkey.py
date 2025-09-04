# Generated migration to convert scheme and lang fields to ForeignKey

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('masterdata', '0003_modify_vocabulary_add_language_scheme'),
    ]

    operations = [
        # Remove existing CharField fields
        migrations.RemoveField(
            model_name='vocabulary',
            name='scheme',
        ),
        migrations.RemoveField(
            model_name='vocabulary',
            name='lang',
        ),
        migrations.RemoveField(
            model_name='historicalvocabulary',
            name='scheme',
        ),
        migrations.RemoveField(
            model_name='historicalvocabulary',
            name='lang',
        ),
        
        # Add ForeignKey fields
        migrations.AddField(
            model_name='vocabulary',
            name='scheme',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='vocabularies', to='masterdata.scheme', verbose_name='طرح کلی'),
        ),
        migrations.AddField(
            model_name='vocabulary',
            name='lang',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='vocabularies', to='masterdata.language', verbose_name='زبان'),
        ),
        migrations.AddField(
            model_name='historicalvocabulary',
            name='scheme',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='masterdata.scheme', verbose_name='طرح کلی'),
        ),
        migrations.AddField(
            model_name='historicalvocabulary',
            name='lang',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='masterdata.language', verbose_name='زبان'),
        ),
    ]
