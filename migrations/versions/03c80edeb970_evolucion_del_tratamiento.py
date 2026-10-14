"""evolucion del tratamiento

Revision ID: 03c80edeb970
Revises: 3d8b41bfc0b3
Create Date: 2026-09-04 18:53:17.477040

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '03c80edeb970'
down_revision = '3d8b41bfc0b3'
branch_labels = None
depends_on = None


def upgrade():
    # NOTA: esta migración quedó duplicada. La tabla 'treatment_evolution_photo'
    # (con estas mismas columnas) ya la crea la migración anterior
    # 3d8b41bfc0b3, por lo que originalmente acá fallaba con
    # "table treatment_evolution_photo already exists" en una instalación nueva.
    # Se convierte en no-op: el contenido real de la tabla es el de
    # 3d8b41bfc0b3 y coincide con models.TreatmentEvolutionPhoto.
    #
    # Se mantiene el revision ID (03c80edeb970) para que las bases de datos ya
    # migradas (con alembic_version en este punto o más adelante) sigan siendo
    # válidas: `flask db upgrade` no vuelve a ejecutar migraciones ya aplicadas.
    pass


def downgrade():
    # Nada que deshacer: la tabla la crea (y la borra) 3d8b41bfc0b3.
    pass
