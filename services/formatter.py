TWO_FACE_LAYOUTS = {
    "adventure",
    "transform",
    "prepare",
    "split",
    "flip",
    "modal_dfc"
}


def format_card(card_json):
    if not card_json:
        return "Card not found.\n\n"

    layout = card_json.get("layout", "")
    name = card_json.get("name", "")

    parts = ["===== CARD ====="]
    parts.append(name)
    parts.append(f"Layout:{layout}")

    if layout in TWO_FACE_LAYOUTS:
        faces = card_json["card_faces"]

        #parts.append("\n")

        face_count = 1

        for face in faces:

            parts.append(f"[FACE {face_count}]")

            face_name = face.get("name", "")
            face_mana = face.get("mana_cost", "")
            face_type = face.get("type_line", "")
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

            #parts.append("\n")
            face_count += 1

        return "\n".join(parts) + "\n\n"

    else:

        parts.append("[FACE 1]")

        mana = card_json.get("mana_cost", "")
        type_line = card_json.get("type_line", "")
        oracle = card_json.get("oracle_text", "")
        power = card_json.get("power", "")
        toughness = card_json.get("toughness", "")

        if mana:
            parts.append(mana)

        if type_line:
            parts.append(f"Type: {type_line}")

        if oracle:
            parts.append("\n" + oracle)

        if power and toughness:
            parts.append(f"\n{power}/{toughness}")

        return "\n".join(parts) + "\n\n"


def build_output(deck_format, cleaned_lines, formatted_cards):
    parts = []

    card_index = 0

    for line in deck_format:
        if line == "card_detail":
            parts.append(formatted_cards[card_index])
            card_index += 1
        else:
            parts.append(line)



    #for line in cleaned_lines:
        #parts.append(line)

    #parts.append("\n========== CARD DETAILS ==========\n")

    #for card_text in formatted_cards:
        #parts.append(card_text)

    return "\n".join(parts)
