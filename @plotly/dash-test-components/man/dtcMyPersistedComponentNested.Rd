% Auto-generated: do not edit by hand
\name{dtcMyPersistedComponentNested}

\alias{dtcMyPersistedComponentNested}

\title{MyPersistedComponentNested component}

\description{
Adapted dcc input component for persistence tests.  Note that unnecessary props have been removed.
}

\usage{
dtcMyPersistedComponentNested(id=NULL, value=NULL, name=NULL, persistence=NULL,
persisted_props=NULL, persistence_type=NULL)
}

\arguments{
\item{id}{Character. The ID of this component, used to identify dash components
in callbacks. The ID needs to be unique across all of the
components in an app.}

\item{value}{Character | numeric. The value of the input}

\item{name}{Character. The name of the control, which is submitted with the form data.}

\item{persistence}{Logical | character | numeric. Used to allow user interactions in this component to be persisted when
the component - or the page - is refreshed. If `persisted` is truthy and
hasn't changed from its previous value, a `value` that the user has
changed while using the app will keep that change, as long as
the new `value` also matches what was given originally.
Used in conjunction with `persistence_type`.}

\item{persisted_props}{List of a value equal to: 'value.nested_value's. Properties whose user interactions will persist after refreshing the
component or the page. Since only `value` is allowed this prop can
normally be ignored.}

\item{persistence_type}{A value equal to: 'local', 'session', 'memory'. Where persisted user changes will be stored:
memory: only kept in memory, reset on page refresh.
local: window.localStorage, data is kept after the browser quit.
session: window.sessionStorage, data is cleared once the browser quit.}
}

\value{named list of JSON elements corresponding to React.js properties and their values}

