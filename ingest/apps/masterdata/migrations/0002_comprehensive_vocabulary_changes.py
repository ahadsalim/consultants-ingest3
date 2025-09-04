# Comprehensive migration for Vocabulary model changes and new Language/Scheme models

from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import simple_history.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('masterdata', '0001_initial'),
    ]

    operations = [
        # Update model options first
        migrations.AlterModelOptions(
            name='historicalvocabulary',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical موضوع', 'verbose_name_plural': 'historical موضوعات'},
        ),
        migrations.AlterModelOptions(
            name='historicalvocabularyterm',
            options={'get_latest_by': ('history_date', 'history_id'), 'ordering': ('-history_date', '-history_id'), 'verbose_name': 'historical واژه', 'verbose_name_plural': 'historical واژگان'},
        ),
        migrations.AlterModelOptions(
            name='vocabulary',
            options={'ordering': ['name'], 'verbose_name': 'موضوع', 'verbose_name_plural': 'موضوعات'},
        ),
        migrations.AlterModelOptions(
            name='vocabularyterm',
            options={'ordering': ['vocabulary__name', 'term'], 'verbose_name': 'واژه', 'verbose_name_plural': 'واژگان'},
        ),
        
        # Note: description field removal not needed as it doesn't exist in current schema
        
        # Create Language model
        migrations.CreateModel(
            name='Language',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=100, verbose_name='نام')),
                ('code', models.CharField(max_length=10, unique=True, verbose_name='کد')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
            ],
            options={
                'verbose_name': 'زبان',
                'verbose_name_plural': 'زبان‌ها',
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        
        # Create Scheme model
        migrations.CreateModel(
            name='Scheme',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=200, verbose_name='نام')),
                ('code', models.CharField(max_length=50, unique=True, verbose_name='کد')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
            ],
            options={
                'verbose_name': 'طرح کلی',
                'verbose_name_plural': 'طرح‌های کلی',
                'ordering': ['name'],
            },
            bases=(models.Model,),
        ),
        
        # Create Historical models
        migrations.CreateModel(
            name='HistoricalLanguage',
            fields=[
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(blank=True, editable=False)),
                ('name', models.CharField(max_length=100, verbose_name='نام')),
                ('code', models.CharField(db_index=True, max_length=10, verbose_name='کد')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=models.deletion.SET_NULL, related_name='+', to='auth.user')),
            ],
            options={
                'verbose_name': 'historical زبان',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalScheme',
            fields=[
                ('id', models.UUIDField(db_index=True, default=uuid.uuid4, editable=False)),
                ('created_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(blank=True, editable=False)),
                ('name', models.CharField(max_length=200, verbose_name='نام')),
                ('code', models.CharField(db_index=True, max_length=50, verbose_name='کد')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال')),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField()),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
                ('history_user', models.ForeignKey(null=True, on_delete=models.deletion.SET_NULL, related_name='+', to='auth.user')),
            ],
            options={
                'verbose_name': 'historical طرح کلی',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': 'history_date',
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        
        # Add ForeignKey fields to Vocabulary
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
