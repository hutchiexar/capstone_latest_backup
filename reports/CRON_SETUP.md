# Setting Up Scheduled Reports

To run scheduled reports automatically, you need to set up a scheduled task (cron job) to run the `run_scheduled_reports` management command.

## Linux/Unix Cron Setup

1. Open your crontab file:
   ```
   crontab -e
   ```

2. Add the following line to run the command every hour:
   ```
   0 * * * * cd /path/to/your/project && /path/to/your/virtualenv/bin/python manage.py run_scheduled_reports >> /path/to/logs/scheduled_reports.log 2>&1
   ```

3. Save and exit the editor.

## Windows Task Scheduler Setup

1. Open Task Scheduler (search for "Task Scheduler" in the Start menu)
2. Click "Create Basic Task..."
3. Enter a name (e.g., "Traffic System - Run Scheduled Reports") and description
4. Set the trigger to "Daily" and configure it to recur every 1 hour
5. Choose "Start a program" as the action
6. For the program/script, browse to your Python interpreter in your virtual environment:
   ```
   C:\path\to\venv\Scripts\python.exe
   ```
7. Add arguments:
   ```
   manage.py run_scheduled_reports
   ```
8. Set the "Start in" field to your project directory:
   ```
   C:\path\to\project
   ```
9. Complete the wizard, checking "Open the Properties dialog..." before finishing
10. In the Properties dialog, go to the "Settings" tab and check "Run task as soon as possible after a scheduled start is missed"
11. Click OK to save

## Docker/Container Setup

If you're using Docker or another containerized setup, add the following to your `crontab` file in the appropriate container:

```
# Run scheduled reports every hour
0 * * * * python /app/manage.py run_scheduled_reports >> /var/log/scheduled_reports.log 2>&1
```

Or use a dedicated scheduler service like Celery Beat with tasks configured in your settings:

```python
# settings.py
CELERY_BEAT_SCHEDULE = {
    'run-scheduled-reports-hourly': {
        'task': 'reports.tasks.run_scheduled_reports',
        'schedule': 3600.0,  # Every hour
    },
}
```

## Testing the Scheduler

To test that your setup is working correctly, you can run the command manually with the `--force` flag:

```
python manage.py run_scheduled_reports --force
```

This will process all active scheduled reports, regardless of their next run time.

## Troubleshooting

- **Permission Issues**: Ensure the user running the cron job has appropriate permissions to run the command and write to any output files.
  
- **Environment Variables**: If your application relies on environment variables, make sure they're available in the cron environment.

- **Log Output**: Always configure the cron job to output logs so you can diagnose issues:
  ```
  >> /path/to/logs/scheduled_reports.log 2>&1
  ```

- **Python Path**: If you encounter module import errors, you may need to set the PYTHONPATH environment variable in your cron job. 