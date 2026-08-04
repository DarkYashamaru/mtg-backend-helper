def build_type_line(face):
    left_parts = [*face.get("supertypes", []), *face.get("card_types", [])]
    right_parts = face.get("subtypes", [])

    left = " ".join(part for part in left_parts if part)
    right = " ".join(part for part in right_parts if part)

    if left and right:
        return f"{left} - {right}"

    return left or right


def format_card(card):
    if not card:
        return "Card not found.\n\n"

    layout = card.get("layout", "")
    name = card.get("name", "")
    faces = card.get("faces", [])

    parts = ["===== CARD =====", name, f"Layout:{layout}"]

    for index, face in enumerate(faces, start=1):
        parts.append(f"[FACE {index}]")

        face_name = face.get("name", "")
        face_mana = face.get("mana_cost", "")
        face_type = build_type_line(face)
        face_oracle = face.get("oracle_text", "")
        face_power = face.get("power", "")
        face_toughness = face.get("toughness", "")

        if face_name:
            parts.append(face_name)

        if face_mana:
            parts.append(face_mana)

        if face_type:
            parts.append(f"Type: {face_type}")

        if face_oracle:
            parts.append("\n" + face_oracle)

        if face_power and face_toughness:
            parts.append(f"\n{face_power}/{face_toughness}")

    return "\n".join(parts) + "\n\n"


def build_output(deck_format, formatted_cards):
    parts = []

    card_index = 0

    for line in deck_format:
        if line == "card_detail":
            parts.append(formatted_cards[card_index])
            card_index += 1
        else:
            parts.append(line)



    return "\n".join(parts)
