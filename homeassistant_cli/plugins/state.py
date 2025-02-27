"""Entity plugin for Home Assistant CLI (hass-cli)."""
import json as json_
import logging
import re
from typing import Any, Dict, List, Pattern  # noqa

import click

import homeassistant_cli.autocompletion as autocompletion
from homeassistant_cli.cli import pass_context
from homeassistant_cli.config import Configuration
import homeassistant_cli.const as const
import homeassistant_cli.helper as helper
import homeassistant_cli.remote as api

_LOGGING = logging.getLogger(__name__)


@click.group('state')
@pass_context
def cli(ctx):
    """Get info on entity state from Home Assistant."""


@cli.command()
@click.argument(
    'entity',
    required=True,
    shell_complete=autocompletion.entities,  # type: ignore
)
@pass_context
def get(ctx: Configuration, entity):
    """Get/read entity state from Home Assistant."""
    ctx.auto_output("table")
    state = api.get_state(ctx, entity)

    if state:
        ctx.echo(
            helper.format_output(
                ctx,
                [state],
                columns=ctx.columns if ctx.columns else const.COLUMNS_ENTITIES,
            )
        )
    else:
        _LOGGING.error("Entity with ID: '%s' not found.", entity)


@cli.command()
@click.argument(
    'entity',
    required=True,
    shell_complete=autocompletion.entities,  # type: ignore
)
@pass_context
def delete(ctx: Configuration, entity):
    """Delete entity state from Home Assistant."""
    ctx.auto_output("table")
    deleted = api.remove_state(ctx, entity)

    if deleted:
        ctx.echo("State for entity %s deleted.", entity)
    else:
        ctx.echo("Entity %s not found.", entity)


@cli.command('list')
@click.argument('entityfilter', default=".*", required=False)
@pass_context
def list(ctx, entityfilter):
    """List all state from Home Assistant."""
    ctx.auto_output("table")
    states = api.get_states(ctx)
    entity_filter = entityfilter

    result = []  # type: List[Dict]
    if entity_filter == ".*":
        result = states
    else:
        entity_filter_re = re.compile(entity_filter)  # type: Pattern

        for entity in states:
            if entity_filter_re.search(entity['entity_id']):
                result.append(entity)
    ctx.echo(
        helper.format_output(
            ctx,
            result,
            columns=ctx.columns if ctx.columns else const.COLUMNS_ENTITIES,
        )
    )


@cli.command()
@click.argument(
    'entity',
    required=True,
    shell_complete=autocompletion.entities,  # type: ignore
)
@click.argument('newstate', required=False)
@click.option(
    '--attributes',
    help="Comma separated key/value pairs to use as attributes.",
)
@click.option(
    '--json',
    help="Raw JSON state to use for setting. Overrides any other"
    "state values provided.",
)
@click.option(
    '--merge',
    is_flag=True,
    default=False,
    help="If set and the entity state exists the state and attributes will"
    "be merged into the state rather than overwrite.",
    show_default=True,
)
@pass_context
def edit(ctx: Configuration, entity, newstate, attributes, merge, json):
    """Edit entity state from Home Assistant."""
    ctx.auto_output('data')
    new_state = newstate
    if json:
        _LOGGING.debug(
            "JSON found overriding/creating new state for entity %s", entity
        )
        wanted_state = json_.loads(json)
    elif new_state or attributes:
        wanted_state = {}
        existing_state = api.get_state(ctx, entity)

        if existing_state:
            ctx.echo("Existing state found for %s", entity)
            if merge:
                wanted_state = existing_state
        else:
            ctx.echo("No existing state found for '%s'", entity)

        if attributes:
            attributes_dict = helper.to_attributes(attributes)

            new_attr = wanted_state.get('attributes', {})
            new_attr.update(attributes_dict)
            # This is not honoring merge!
            wanted_state['attributes'] = new_attr

        if newstate:
            wanted_state['state'] = newstate
        else:
            if not existing_state:
                raise ValueError("No new or existing state provided.")
            wanted_state['state'] = existing_state['state']

    else:
        existing = api.get_state(ctx, entity)
        if existing:
            existing_raw = helper.raw_format_output(
                ctx.output, existing, ctx.yaml()
            )
        else:
            existing_raw = helper.raw_format_output(ctx.output, {}, ctx.yaml())

        new = click.edit(existing_raw, extension='.{}'.format(ctx.output))

        if new is not None:
            ctx.echo("Updating '%s'", entity)
            if ctx.output == 'yaml':
                wanted_state = ctx.yamlload(new)
            if ctx.output == 'json':
                wanted_state = json_.loads(new)

            api.set_state(ctx, entity, wanted_state)
        else:
            ctx.echo("No edits/changes returned from editor.")
            return

    _LOGGING.debug("wanted: %s", str(wanted_state))
    result = api.set_state(ctx, entity, wanted_state)
    ctx.echo("Entity %s updated successfully", entity)
    _LOGGING.debug("Updated to: %s", result)


def _report(ctx: Configuration, result: List[Dict[str, Any]], action: str):
    """Create a report."""
    ctx.echo(
        helper.format_output(
            ctx,
            result,
            columns=ctx.columns if ctx.columns else const.COLUMNS_ENTITIES,
        )
    )
    if ctx.verbose:
        ctx.echo("%s entities reported to be %s", len(result), action)


def _homeassistant_cmd(ctx: Configuration, entities, cmd, action):
    """Run command on Home Assistant."""
    data = {'entity_id': entities}
    _LOGGING.debug("%s on %s", cmd, entities)
    result = api.call_service(ctx, 'homeassistant', cmd, data)

    _report(ctx, result, action)


@cli.command()
@click.argument(
    'entities',
    nargs=-1,
    required=True,
    shell_complete=autocompletion.entities,  # type: ignore
)
@pass_context
def toggle(ctx: Configuration, entities):
    """Toggle state for one or more entities in Home Assistant."""
    ctx.auto_output("table")
    _homeassistant_cmd(ctx, entities, 'toggle', "toggled")


@cli.command('turn_off')
@click.argument(
    'entities',
    nargs=-1,
    required=True,
    shell_complete=autocompletion.entities,  # type: ignore
)
@pass_context
def off_cmd(ctx: Configuration, entities):
    """Turn entity off."""
    ctx.auto_output("table")
    _homeassistant_cmd(ctx, entities, 'turn_off', "turned off")


@cli.command('turn_on')
@click.argument(
    'entities',
    nargs=-1,
    required=True,
    shell_complete=autocompletion.entities,  # type: ignore
)
@pass_context
def on_cmd(ctx: Configuration, entities):
    """Turn entity on."""
    ctx.auto_output("table")
    _homeassistant_cmd(ctx, entities, 'turn_on', "turned on")


@cli.command()
@click.argument(
    'entities',
    nargs=-1,
    required=True,
    shell_complete=autocompletion.entities,  # type: ignore
)
@click.option(
    '--since',
    required=False,
    default="1d",
    help="Start of the period to get history from. A timestamp or relative "
    "expression relative to now. Defaults to 1 day.",
)
@click.option(
    '--end',
    required=False,
    default="now",
    help="End of the period to query history from. A timestamp or relative "
    "expression relative to now. Defaults to now.",
)
@pass_context
def history(ctx: Configuration, entities: List, since: str, end: str):
    """Get state history from Home Assistant, all or per entity.

    You can use `--since` and `--end` to narrow or expand the time period.

    Both options accepts a full timestamp i.e. `2016-02-06T22:15:00+00:00`
    or a relative expression i.e. `3m` for three minutes, `5d` for 5 days.
    Even `3 minutes` or `5 days` will work.
    See https://dateparser.readthedocs.io/en/latest/#features for examples.
    """
    import dateparser

    ctx.auto_output("table")
    settings = {
        'DATE_ORDER': 'DMY',
        'TIMEZONE': 'UTC',
        'RETURN_AS_TIMEZONE_AWARE': True,
    }

    start_time = dateparser.parse(since, settings=settings)

    end_time = dateparser.parse(end, settings=settings)

    delta = end_time - start_time

    if ctx.verbose:
        click.echo(
            'Querying from {}:{} to {}:{} a span of {}'.format(
                since, start_time.isoformat(), end, end_time.isoformat(), delta
            )
        )

    data = api.get_history(ctx, list(entities), start_time, end_time)

    result = []  # type: List[Dict[str, Any]]
    entity_count = 0
    for item in data:
        result.extend(item)  # type: ignore
        entity_count = entity_count + 1

    click.echo(
        helper.format_output(
            ctx,
            result,
            columns=ctx.columns if ctx.columns else const.COLUMNS_ENTITIES,
        )
    )

    if ctx.verbose:
        click.echo(
            'History with {} rows from {} entities found.'.format(
                len(result), entity_count
            )
        )
