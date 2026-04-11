#!/usr/bin/env python3
"""
Test rápido del sistema de skills evolutivas
"""

import sys
sys.path.append('.')

def test_openclaw_system():
    print("🧪 Testing sistema de skills evolutivas...")

    # Test básico sin importar modelo completo
    try:
        from skill_factory import SkillFactory, EvolutiveSkill, SkillContext

        # Crear skill factory básico
        class MockSkillManager:
            def __init__(self):
                self.base_skills = {}

        skill_factory = SkillFactory(MockSkillManager())

        # Test 1: Crear skill desde template
        print("📝 Test 1: Creando skill desde template...")
        skill = skill_factory.create_skill_from_template("data_analyzer", {
            "name": "test_analyzer",
            "description": "Skill de prueba para análisis"
        })

        if skill and skill.compile():
            print("✅ Skill compilado exitosamente")
        else:
            print(f"❌ Error compilando skill: {skill.compile_errors if skill else 'Skill no creado'}")
            return False

        # Test 2: Crear skill personalizado
        print("🔨 Test 2: Creando skill personalizado...")
        custom_code = '''
def execute(multiplicador=1, **kwargs):
    # Simulación simple sin contexto real
    resultado = 50 * multiplicador
    return f"Recursos multiplicados: {resultado}"
'''

        custom_skill = skill_factory.create_skill_from_code(
            "calculadora_recursos",
            "Calcula recursos multiplicados",
            custom_code,
            "test_user"
        )

        if custom_skill and custom_skill.compile():
            print("✅ Skill personalizado compilado")

            # Crear contexto mock mínimo
            class MockAgente:
                def __init__(self):
                    self.unique_id = "test_agent"
                    self.x, self.y = 10, 10

            class MockMundo:
                def __init__(self):
                    self.step = 1

            class MockSkillManager:
                pass

            context = SkillContext(MockAgente(), MockMundo(), MockSkillManager())

            result = custom_skill.execute(context, multiplicador=3)
            if result.get("success"):
                print(f"✅ Skill personalizado ejecutado: {result['result']}")
            else:
                print(f"❌ Error: {result.get('error')}")
        else:
            print("❌ Error compilando skill personalizado")

        print("🎉 Tests básicos completados!")
        return True

    except Exception as e:
        print(f"❌ Error en test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_openclaw_system()