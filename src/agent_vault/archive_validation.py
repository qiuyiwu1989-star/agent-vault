"""Shared private archive validation. No publishing capability or network access."""
import copy
import json
from urllib.parse import urlsplit

TYPES = ('article', 'book', 'media', 'note', 'discussion', 'brief', 'work')
FIELDS = {'type', 'title', 'body', 'sources', 'tags', 'participants', 'coverage', 'visibility', 'sections'}


def validate(payload, stage='receive'):
    errors, warnings = [], []
    def error(rule, path, message):
        errors.append(dict(rule=rule, path=path, message=message))
    if stage not in ('receive', 'archive', 'publish'):
        error('stage.invalid', 'stage', 'Unknown validation stage')
    if stage == 'publish':
        error('publish.unsupported', 'stage', 'Private archive publishing is not supported')
    if not isinstance(payload, dict):
        error('record.object', '$', 'Record must be an object')
        return dict(valid=False, errors=errors, warnings=warnings, normalized=None)
    try:
        size = len(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode('utf-8'))
        if size > 1_000_000:
            error('record.size', '$', 'Record must fit within 1000000 UTF-8 JSON bytes; split large material into linked records')
    except (ValueError, TypeError, UnicodeError):
        error('record.json', '$', 'Record must be valid JSON data')
        return dict(valid=False, errors=errors, warnings=warnings, normalized=None)
    record = copy.deepcopy(payload)
    for key in set(record) - FIELDS:
        error('field.unknown', str(key), 'Unknown record field')
    if record.get('type') not in TYPES:
        error('type.invalid', 'type', 'Choose one of: ' + ', '.join(TYPES))
    for field, limit in [('title', 300), ('body', 2000000), ('coverage', 4000)]:
        value = record.get(field, '')
        if not isinstance(value, str) or len(value) > limit:
            error('text.invalid', field, 'Expected a string of at most %s characters' % limit)
        else:
            record[field] = value.strip()
    if not record.get('title'):
        record['title'] = '未命名档案'
        warnings.append(dict(rule='title.placeholder', path='title', message='Temporary title; no factual title inferred'))
    if record.get('visibility', 'private') != 'private':
        error('visibility.private', 'visibility', 'Only private visibility is supported')
    record.setdefault('visibility', 'private')
    source_evidence = False
    sources = record.get('sources', [])
    if not isinstance(sources, list) or len(sources) > 200:
        error('sources.array', 'sources', 'Expected at most 200 sources')
    else:
        for i, source in enumerate(sources):
            path = 'sources[%s]' % i
            if not isinstance(source, dict):
                error('source.object', path, 'Source must be an object')
                continue
            for key in set(source) - {'url', 'description', 'coverage'}:
                error('field.unknown', path + '.' + str(key), 'Unknown source field')
            for key, value in source.items():
                if key not in ('url', 'description', 'coverage'):
                    continue
                if not isinstance(value, str) or len(value) > 8000:
                    error('source.text', path + '.' + key, 'Expected a string of at most 8000 characters')
                    continue
                source[key] = value.strip()
            url = source.get('url', '')
            valid_url = False
            if isinstance(url, str) and url:
                try:
                    parsed = urlsplit(url)
                    valid_url = (parsed.scheme in ('https', 'http') and bool(parsed.hostname)
                                 and not parsed.username and not parsed.password
                                 and not any(c.isspace() for c in url))
                except ValueError:
                    pass
                if not valid_url:
                    error('source.url', path + '.url', 'Expected an HTTP(S) URL without embedded credentials')
            description = source.get('description', '')
            source_evidence |= valid_url or (isinstance(description, str) and bool(description.strip()))
        record['sources'] = sources
    tags = record.get('tags', [])
    if (not isinstance(tags, list) or len(tags) > 30
            or any(not isinstance(t, str) or not t.strip() or len(t) > 100 for t in tags)):
        error('tags.invalid', 'tags', 'Expected at most 30 nonempty string tags')
    else:
        record['tags'] = list(dict.fromkeys(t.strip() for t in tags))
    participants = record.get('participants', [])
    if not isinstance(participants, list) or len(participants) > 100:
        error('participants.array', 'participants', 'Expected at most 100 participants')
    else:
        for i, participant in enumerate(participants):
            path = 'participants[%s]' % i
            if not isinstance(participant, dict):
                error('participant.object', path, 'Participant must be an object')
                continue
            if set(participant) - {'name', 'role'}:
                error('field.unknown', path, 'Participant only accepts name and role')
            for key in ('name', 'role'):
                value = participant.get(key)
                if not isinstance(value, str) or not value.strip() or len(value) > 300:
                    error('participant.text', path + '.' + key, 'Nonempty name and attribution role required')
        record['participants'] = participants
    sections = record.get('sections', [])
    section_content = False
    seen_keys = set()
    if not isinstance(sections, list) or len(sections) > 30:
        error('sections.array', 'sections', 'Expected at most 30 sections')
    else:
        for i, section in enumerate(sections):
            path = 'sections[%s]' % i
            if not isinstance(section, dict):
                error('section.object', path, 'Section must be an object')
                continue
            if set(section) - {'key', 'title', 'text', 'kind'}:
                error('field.unknown', path, 'Unknown section field')
            key = section.get('key')
            if not isinstance(key, str) or not key.strip() or len(key) > 80:
                error('section.key', path + '.key', 'Nonempty key at most 80 characters required')
            elif key in seen_keys:
                error('section.key.duplicate', path + '.key', 'Section key must be unique')
            else:
                seen_keys.add(key)
            for field, limit in [('title', 200), ('text', 100000)]:
                value = section.get(field)
                if not isinstance(value, str) or len(value) > limit:
                    error('section.text', path + '.' + field, 'String required within size limit')
            if section.get('kind') not in ('original', 'summary', 'analysis', 'user_note', 'question'):
                error('section.kind', path + '.kind', 'Unsupported section kind')
            if isinstance(section.get('text'), str) and section['text'].strip():
                section_content = True
        record['sections'] = sections
    if not (isinstance(record.get('body'), str) and record['body'].strip()) and not section_content and not source_evidence:
        error('content.empty', 'body', 'Provide nonempty body or a source URL/description')
    if stage == 'archive':
        if not (isinstance(record.get('body'), str) and record['body'].strip()) and not section_content:
            error('archive.body', 'body', 'Organized archive requires a body')
        if record.get('title') == '未命名档案':
            error('archive.title', 'title', 'Replace temporary title before archiving')
        if record.get('type') in ('article', 'book', 'media', 'brief') and not source_evidence:
            error('archive.sources', 'sources', 'This type requires a source record')
        if record.get('type') in ('article', 'book', 'media', 'discussion', 'brief') and not record.get('coverage'):
            error('archive.coverage', 'coverage', 'State actual input or discussion coverage')
        if record.get('type') == 'discussion' and not participants:
            error('archive.participants', 'participants', 'Discussion needs attributed participants')
        warnings.append(dict(rule='review.required', path='$', message='Structural validation does not establish fidelity, truth, attribution approval or publication readiness'))
    return dict(valid=not errors, errors=errors, warnings=warnings, normalized=record)
