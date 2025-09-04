# Generated migration for Vocabulary model changes and new Language/Scheme models

from django.db import migrations, models
import django.utils.timezone
import simple_history.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('masterdata', '0002_alter_historicalvocabulary_options_and_more'),
    ]

    operations = [
        # Remove description field from Vocabulary
        migrations.RemoveField(
            model_name='vocabulary',
            name='description',
        ),
        migrations.RemoveField(
            model_name='historicalvocabulary',
            name='description',
        ),
        
        # Add new fields to Vocabulary
        migrations.AddField(
            model_name='vocabulary',
            name='scheme',
            field=models.CharField(blank=True, max_length=200, verbose_name='طرح کلی'),
        ),
        migrations.AddField(
            model_name='vocabulary',
            name='lang',
            field=models.CharField(blank=True, max_length=10, verbose_name='زبان'),
        ),
        migrations.AddField(
            model_name='historicalvocabulary',
            name='scheme',
            field=models.CharField(blank=True, max_length=200, verbose_name='طرح کلی'),
        ),
        migrations.AddField(
            model_name='historicalvocabulary',
            name='lang',
            field=models.CharField(blank=True, max_length=10, verbose_name='زبان'),
        ),
        
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
                ('description', models.TextField(blank=True, verbose_name='توضیحات')),
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
                ('description', models.TextField(blank=True, verbose_name='توضیحات')),
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
    ]
