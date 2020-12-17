# AUTO GENERATED FILE - DO NOT EDIT

dtcDelayedEventComponent <- function(id=NULL, n_clicks=NULL) {
    
    props <- list(id=id, n_clicks=n_clicks)
    if (length(props) > 0) {
        props <- props[!vapply(props, is.null, logical(1))]
    }
    component <- list(
        props = props,
        type = 'DelayedEventComponent',
        namespace = 'dash_test_components',
        propNames = c('id', 'n_clicks'),
        package = 'dashTestComponents'
        )

    structure(component, class = c('dash_component', 'list'))
}
