extends Node
## Authority: every authoritative game-state mutation routes through this
## autoload (spawns AND damage now — `damage_player` is right below this
## comment, which used to file it under "later milestones"; loot and
## extraction are the ones still to come). This is
## the seam a future multiplayer server would own — gameplay code must call
## these functions instead of mutating state directly.


func spawn_player(parent: Node, pos: Vector2) -> Player:
	var player := Player.new()
	player.name = "Player"
	player.position = pos
	parent.add_child(player)
	return player


func damage_player(player: Player, bone: String = "", who: String = "") -> void:
	player.take_hit(bone, who)
