# AUTO GENERATED FILE - DO NOT EDIT

dtcMyPersistedComponentNested <- function(id=NULL, value=NULL, name=NULL, persistence=NULL, persisted_props=NULL, persistence_type=NULL) {
    
    props <- list(id=id, value=value, name=name, persistence=persistence, persisted_props=persisted_props, persistence_type=persistence_type)
    if (length(props) > 0) {
        props <- props[!vapply(props, is.null, logical(1))]
    }
    component <- list(
        props = props,
        type = 'MyPersistedComponentNested',
        namespace = 'dash_test_components',
        propNames = c('id', 'value', 'name', 'persistence', 'persisted_props', 'persistence_type'),
        package = 'dashTestComponents'
        )

    structure(component, class = c('dash_component', 'list'))
}
