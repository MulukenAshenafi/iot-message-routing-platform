# Generated manually for Revision 1.1 fixes
# Adds group and nid fields to Owner model

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_owner_api_key_owner_api_key_hash_owner_expired_and_more'),
        ('iot_messages', '0001_initial'),  # messages app uses label 'iot_messages'
    ]

    operations = [
        migrations.AddField(
            model_name='owner',
            name='group',
            field=models.ForeignKey(
                blank=True,
                help_text='Group/Network assigned to owner',
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name='owners',
                to='iot_messages.group'  # messages app uses label 'iot_messages'
            ),
        ),
        migrations.AddField(
            model_name='owner',
            name='nid',
            field=models.CharField(
                blank=True,
                db_index=True,
                help_text='Network ID (NID) - can be auto-generated or manually entered (max 0xFFFFFFFF)',
                max_length=100,
                null=True
            ),
        ),
    ]

