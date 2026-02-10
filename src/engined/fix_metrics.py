import re

with open('tests/test_integration.py', encoding='utf-8') as f:
    content = f.read()

# Replace metrics['key'] with metrics.key
patterns = [
    (r"\.metrics\['total_calls'\]", '.metrics.total_calls'),
    (r"\.metrics\['failed_calls'\]", '.metrics.failed_calls'),
    (r"\.metrics\['successful_calls'\]", '.metrics.successful_calls'),
    (r"\.metrics\['rejected_calls'\]", '.metrics.rejected_calls'),
    (r'\.metrics\["total_calls"\]', '.metrics.total_calls'),
    (r'\.metrics\["failed_calls"\]', '.metrics.failed_calls'),
    (r'\.metrics\["successful_calls"\]', '.metrics.successful_calls'),
    (r'\.metrics\["rejected_calls"\]', '.metrics.rejected_calls'),
]

for pattern, replacement in patterns:
    content = re.sub(pattern, replacement, content)

with open('tests/test_integration.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('Fixed metrics access patterns')
