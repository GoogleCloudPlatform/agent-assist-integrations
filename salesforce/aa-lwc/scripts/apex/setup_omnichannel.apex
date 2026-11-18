// 1. Ensure Permission Set for Omni-Channel Presence Access exists
List<PermissionSet> existingPS = [
    SELECT Id, Name 
    FROM PermissionSet 
    WHERE Name = 'Omni_Presence_Access'
];

PermissionSet ps;
if (existingPS.isEmpty()) {
    ps = new PermissionSet(
        Name = 'Omni_Presence_Access',
        Label = 'Omni Presence Access'
    );
    insert ps;
    System.debug('Created PermissionSet Omni_Presence_Access (ID: ' + ps.Id + ')');
} else {
    ps = existingPS[0];
    System.debug('Found existing PermissionSet Omni_Presence_Access (ID: ' + ps.Id + ')');
}

// 2. Grant access to all ServicePresenceStatus records via SetupEntityAccess
List<ServicePresenceStatus> statuses = [
    SELECT Id, MasterLabel, DeveloperName 
    FROM ServicePresenceStatus
];

List<SetupEntityAccess> existingAccess = [
    SELECT SetupEntityId 
    FROM SetupEntityAccess 
    WHERE ParentId = :ps.Id
];
Set<Id> grantedStatusIds = new Set<Id>();
for (SetupEntityAccess sea : existingAccess) {
    grantedStatusIds.add(sea.SetupEntityId);
}

List<SetupEntityAccess> newAccessList = new List<SetupEntityAccess>();
for (ServicePresenceStatus s : statuses) {
    if (!grantedStatusIds.contains(s.Id)) {
        newAccessList.add(new SetupEntityAccess(
            ParentId = ps.Id,
            SetupEntityId = s.Id
        ));
        System.debug('Granting access to Presence Status: ' + s.MasterLabel + ' (' + s.DeveloperName + ')');
    }
}
if (!newAccessList.isEmpty()) {
    insert newAccessList;
    System.debug('Inserted ' + newAccessList.size() + ' SetupEntityAccess entries.');
}

// 3. Assign Permission Set to current running user
Id currentUserId = UserInfo.getUserId();
List<PermissionSetAssignment> existingPSA = [
    SELECT Id 
    FROM PermissionSetAssignment 
    WHERE AssigneeId = :currentUserId 
      AND PermissionSetId = :ps.Id
];

if (existingPSA.isEmpty()) {
    insert new PermissionSetAssignment(
        AssigneeId = currentUserId,
        PermissionSetId = ps.Id
    );
    System.debug('Assigned Omni_Presence_Access to user ' + UserInfo.getUserName());
} else {
    System.debug('User already assigned to Omni_Presence_Access');
}

System.debug('Omni-Channel setup complete!');
