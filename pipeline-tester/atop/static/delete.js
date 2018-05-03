$(document).ready(function(){
    const DELETE_TYPE_DESCRIPTOR = 0
    const DELETE_TYPE_CARMIN_PLATFORM = 1
    $(".action-delete").click(function () {
        
        var id = $(this).attr("delete-id");
        var type = $(this).attr("delete-type");
        if (type == "descriptor") {
            var type_value = DELETE_TYPE_DESCRIPTOR;
        }
        if (type == "carmin platform") {
            var type_value = DELETE_TYPE_CARMIN_PLATFORM;
        }

        var message = "Are you sure you want to delete this " + type + " ?";
        $("#modalEntryDeletion .modal-title").html("Removal of a " + type);
        $("#modalEntryDeletion .modal-body").html(message);
        $("#modalEntryDeletion #modal-button-delete-yes").attr("delete-id", id);
        $("#modalEntryDeletion #modal-button-delete-yes").attr("delete-type", type_value);
        $("#modalEntryDeletion").modal('toggle');
        
    });
});
