// Assign active user to existing CallCenter definition
CallCenter cc = [SELECT Id, Name, InternalName FROM CallCenter WHERE InternalName = 'GenesysCloud' OR Name LIKE '%Genesys Cloud%' LIMIT 1];
System.debug('Found CallCenter: ' + cc.Name + ' (ID: ' + cc.Id + ')');

Id currentUserId = UserInfo.getUserId();
User u = [SELECT Id, Name, CallCenterId FROM User WHERE Id = :currentUserId];
u.CallCenterId = cc.Id;
update u;
System.debug('Successfully assigned CallCenter ' + cc.Name + ' to user ' + u.Name + ' (' + u.Id + ')');
