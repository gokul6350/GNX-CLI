import threading
import queue
import requests
import time
import uuid
import os
import logging

logger = logging.getLogger(__name__)

class HistoryLogger:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(HistoryLogger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.base_url = "http://127.0.0.1:5000/api"
        self.session_id = str(uuid.uuid4())[:8]
        self.queue = queue.Queue()
        self.running = True
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()
        self._initialized = True
        
        # Create session immediately
        self.create_session()
        
    def create_session(self):
        try:
            requests.post(f"{self.base_url}/session", json={
                "id": self.session_id,
                "name": f"Session {self.session_id}"
            }, timeout=2)
        except Exception as e:
            logger.error(f"Failed to create session: {e}")

    def _worker(self):
        while self.running:
            try:
                task = self.queue.get(timeout=1)
                if task is None:
                    break
                
                endpoint, data, is_file = task
                
                try:
                    if is_file:
                        requests.post(f"{self.base_url}/{endpoint}", files=data, data={'session_id': self.session_id}, timeout=5)
                    else:
                        data['session_id'] = self.session_id
                        requests.post(f"{self.base_url}/{endpoint}", json=data, timeout=5)
                except requests.exceptions.ConnectionError:
                    # Backend might not be running, ignore to avoid spamming logs
                    pass
                except Exception as e:
                    logger.error(f"Logger worker error: {e}")
                    
                self.queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"Worker loop error: {e}")

    def log(self, type, content, is_context=False, metadata=None):
        """
        Log a text entry.
        type: user, ai, tool_call, tool_result, system
        """
        data = {
            "type": type,
            "content": str(content),
            "is_context": is_context,
            "metadata": metadata or {}
        }
        self.queue.put(("log", data, False))

    def log_image(self, image_path):
        """Log an image file."""
        if not os.path.exists(image_path):
            return
            
        try:
            # We need to read the file here or pass the path. 
            # Since requests needs an open file, let's open it in the worker or pass the content.
            # Better to pass path and let worker open it, but worker might be delayed.
            # Let's read it into memory if small, or just pass path if we trust it persists.
            # For simplicity, let's just queue the path and let worker handle it.
            # Wait, requests.post files arg expects a file-like object.
            
            # Actually, let's just do it in the worker to avoid blocking here.
            # But we need to be careful about file closing.
            
            # Let's just read it now.
            with open(image_path, 'rb') as f:
                file_content = f.read()
                
            filename = os.path.basename(image_path)
            files = {'image': (filename, file_content)}
            self.queue.put(("image", files, True))
            
        except Exception as e:
            logger.error(f"Failed to queue image: {e}")

    def stop(self):
        self.running = False
        self.queue.put(None)
        self.worker_thread.join(timeout=2)

# Global instance
history_logger = HistoryLogger()
