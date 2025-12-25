"""
Progressive batch processing utilities for business card OCR.
Handles batch processing with real-time progress updates.
"""

import json
import time
import uuid
from typing import Dict, List, Generator, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class ProgressiveBatchProcessor:
    """Handles progressive batch processing with real-time updates."""
    
    def __init__(self, batch_size: int = 20):
        """
        Initialize processor.
        
        Args:
            batch_size: Number of cards to process in each batch
        """
        self.batch_size = batch_size
        self.active_jobs = {}  # Store active processing jobs
    
    def start_batch_job(self, image_paths: List[Path], job_id: Optional[str] = None) -> str:
        """
        Start a new batch processing job.
        
        Args:
            image_paths: List of image paths to process
            job_id: Optional job ID (generates one if not provided)
            
        Returns:
            Job ID for tracking progress
        """
        if job_id is None:
            job_id = str(uuid.uuid4())
        
        # Split images into batches
        batches = [
            image_paths[i:i + self.batch_size] 
            for i in range(0, len(image_paths), self.batch_size)
        ]
        
        self.active_jobs[job_id] = {
            'status': 'started',
            'total_images': len(image_paths),
            'processed': 0,
            'successful': 0,
            'failed': 0,
            'current_batch': 0,
            'total_batches': len(batches),
            'batches': batches,
            'results': [],
            'started_at': time.time(),
            'last_update': time.time()
        }
        
        logger.info(f"Started batch job {job_id} with {len(image_paths)} images in {len(batches)} batches")
        return job_id
    
    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """Get current status of a batch job."""
        return self.active_jobs.get(job_id)
    
    def process_next_batch(self, job_id: str, pipeline) -> Optional[Dict]:
        """
        Process the next batch for a job.
        
        Args:
            job_id: Job ID
            pipeline: OCR pipeline instance
            
        Returns:
            Batch results or None if job complete/not found
        """
        if job_id not in self.active_jobs:
            return None
        
        job = self.active_jobs[job_id]
        
        # Check if job is complete
        if job['current_batch'] >= job['total_batches']:
            job['status'] = 'completed'
            return None
        
        # Process current batch
        batch_images = job['batches'][job['current_batch']]
        batch_results = []
        
        job['status'] = f"processing_batch_{job['current_batch'] + 1}"
        
        for image_path in batch_images:
            try:
                result = pipeline.process_image(image_path, enrich=False)  # Skip enrichment for speed
                batch_results.append({
                    'image': str(image_path),
                    'result': result
                })
                
                if result.get('success'):
                    job['successful'] += 1
                else:
                    job['failed'] += 1
                    
                job['processed'] += 1
                job['last_update'] = time.time()
                
            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
                batch_results.append({
                    'image': str(image_path),
                    'result': {
                        'success': False,
                        'error': str(e)
                    }
                })
                job['failed'] += 1
                job['processed'] += 1
        
        # Add batch results to job
        job['results'].extend(batch_results)
        job['current_batch'] += 1
        
        # Calculate progress
        progress = (job['processed'] / job['total_images']) * 100
        
        return {
            'job_id': job_id,
            'batch_number': job['current_batch'],
            'total_batches': job['total_batches'],
            'batch_results': batch_results,
            'progress': progress,
            'processed': job['processed'],
            'successful': job['successful'],
            'failed': job['failed'],
            'total': job['total_images'],
            'status': job['status'],
            'is_complete': job['current_batch'] >= job['total_batches']
        }
    
    def cleanup_job(self, job_id: str) -> bool:
        """Remove a completed job from memory."""
        if job_id in self.active_jobs:
            del self.active_jobs[job_id]
            return True
        return False

# Global processor instance
batch_processor = ProgressiveBatchProcessor()