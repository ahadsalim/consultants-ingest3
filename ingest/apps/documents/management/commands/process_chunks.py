"""
Management command for processing chunks and embeddings.
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from ingest.apps.documents.models import InstrumentExpression, LegalUnit
from ingest.apps.documents.services import chunk_processing_service


class Command(BaseCommand):
    help = 'Process legal units to create chunks and embeddings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--expression-id',
            type=str,
            help='Process specific expression by ID',
        )
        parser.add_argument(
            '--unit-id',
            type=str,
            help='Process specific legal unit by ID',
        )
        parser.add_argument(
            '--all',
            action='store_true',
            help='Process all expressions',
        )
        parser.add_argument(
            '--cleanup-duplicates',
            action='store_true',
            help='Clean up duplicate chunks',
        )

    def handle(self, *args, **options):
        if options['cleanup_duplicates']:
            self.cleanup_duplicates()
            return

        if options['expression_id']:
            self.process_expression(options['expression_id'])
        elif options['unit_id']:
            self.process_unit(options['unit_id'])
        elif options['all']:
            self.process_all_expressions()
        else:
            self.stdout.write(
                self.style.ERROR('Please specify --expression-id, --unit-id, --all, or --cleanup-duplicates')
            )

    def process_expression(self, expression_id):
        """Process a specific expression."""
        try:
            expression = InstrumentExpression.objects.get(id=expression_id)
            self.stdout.write(f'Processing expression: {expression}')
            
            results = chunk_processing_service.process_expression(expression)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully processed expression {expression_id}:\n'
                    f'  - Units processed: {results["units_processed"]}\n'
                    f'  - Chunks created: {results["chunks_created"]}\n'
                    f'  - Embeddings created: {results["embeddings_created"]}\n'
                    f'  - Errors: {len(results["errors"])}'
                )
            )
            
            if results['errors']:
                for error in results['errors']:
                    self.stdout.write(self.style.WARNING(f'  Error: {error}'))
                    
        except InstrumentExpression.DoesNotExist:
            raise CommandError(f'Expression with ID {expression_id} does not exist')

    def process_unit(self, unit_id):
        """Process a specific legal unit."""
        try:
            unit = LegalUnit.objects.get(id=unit_id)
            self.stdout.write(f'Processing legal unit: {unit}')
            
            results = chunk_processing_service.process_legal_unit(unit)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully processed unit {unit_id}:\n'
                    f'  - Chunks created: {results["chunks_created"]}\n'
                    f'  - Embeddings created: {results["embeddings_created"]}'
                )
            )
            
        except LegalUnit.DoesNotExist:
            raise CommandError(f'Legal unit with ID {unit_id} does not exist')

    def process_all_expressions(self):
        """Process all expressions."""
        expressions = InstrumentExpression.objects.all()
        total_expressions = expressions.count()
        
        if total_expressions == 0:
            self.stdout.write(self.style.WARNING('No expressions found to process'))
            return

        self.stdout.write(f'Processing {total_expressions} expressions...')
        
        total_results = {
            'expressions_processed': 0,
            'units_processed': 0,
            'chunks_created': 0,
            'embeddings_created': 0,
            'errors': []
        }
        
        for i, expression in enumerate(expressions, 1):
            self.stdout.write(f'Processing expression {i}/{total_expressions}: {expression}')
            
            try:
                results = chunk_processing_service.process_expression(expression)
                total_results['expressions_processed'] += 1
                total_results['units_processed'] += results['units_processed']
                total_results['chunks_created'] += results['chunks_created']
                total_results['embeddings_created'] += results['embeddings_created']
                total_results['errors'].extend(results['errors'])
                
            except Exception as e:
                error_msg = f'Error processing expression {expression.id}: {str(e)}'
                self.stdout.write(self.style.ERROR(error_msg))
                total_results['errors'].append(error_msg)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Completed processing all expressions:\n'
                f'  - Expressions processed: {total_results["expressions_processed"]}/{total_expressions}\n'
                f'  - Units processed: {total_results["units_processed"]}\n'
                f'  - Chunks created: {total_results["chunks_created"]}\n'
                f'  - Embeddings created: {total_results["embeddings_created"]}\n'
                f'  - Total errors: {len(total_results["errors"])}'
            )
        )

    def cleanup_duplicates(self):
        """Clean up duplicate chunks."""
        from django.db.models import Count
        from ingest.apps.documents.models import Chunk
        
        self.stdout.write('Cleaning up duplicate chunks...')
        
        # Find duplicate hashes
        duplicates = (
            Chunk.objects
            .values('expr', 'hash')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )
        
        deleted_count = 0
        for duplicate in duplicates:
            # Keep the first chunk, delete the rest
            chunks = Chunk.objects.filter(
                expr=duplicate['expr'],
                hash=duplicate['hash']
            ).order_by('created_at')
            
            for chunk in chunks[1:]:  # Skip the first one
                chunk.delete()
                deleted_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Cleaned up {deleted_count} duplicate chunks')
        )
